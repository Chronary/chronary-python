"""Tests for chronary.webhook.verify_signature and unwrap.

Chronary signs HMAC over ``{timestamp}.{payload}`` — not over payload alone.
These tests exercise that signing scheme + the replay-tolerance window.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest

from chronary.webhook import (
    SignatureVerificationError,
    unwrap,
    verify_signature,
)

SECRET = "whsec_test_secret_123"


def _sign(payload: bytes, timestamp: str, secret: str = SECRET) -> str:
    message = f"{timestamp}.".encode("utf-8") + payload
    return "sha256=" + hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def _valid_headers(payload: bytes, *, ts: int | None = None) -> dict[str, str]:
    ts_str = str(ts if ts is not None else int(time.time()))
    return {
        "X-Signature": _sign(payload, ts_str),
        "X-Timestamp": ts_str,
        "X-Chronary-Event-Type": "event.created",
    }


class TestVerifySignature:
    def test_valid_signature(self) -> None:
        payload = b'{"event":"event.created","data":{}}'
        verify_signature(payload, _valid_headers(payload), secret=SECRET)

    def test_valid_signature_string_payload(self) -> None:
        payload_str = '{"event":"event.created","data":{}}'
        payload_bytes = payload_str.encode("utf-8")
        verify_signature(payload_str, _valid_headers(payload_bytes), secret=SECRET)

    def test_tampered_payload(self) -> None:
        payload = b'{"event":"event.created","data":{}}'
        headers = _valid_headers(payload)
        tampered = b'{"event":"event.deleted","data":{}}'
        with pytest.raises(SignatureVerificationError, match="mismatch"):
            verify_signature(tampered, headers, secret=SECRET)

    def test_wrong_secret(self) -> None:
        payload = b'{"event":"event.created"}'
        with pytest.raises(SignatureVerificationError, match="mismatch"):
            verify_signature(payload, _valid_headers(payload), secret="wrong")

    def test_missing_signature_header(self) -> None:
        payload = b'{"event":"event.created"}'
        headers = _valid_headers(payload)
        del headers["X-Signature"]
        with pytest.raises(SignatureVerificationError, match="Missing X-Signature"):
            verify_signature(payload, headers, secret=SECRET)

    def test_missing_timestamp_header(self) -> None:
        payload = b'{"event":"event.created"}'
        headers = _valid_headers(payload)
        del headers["X-Timestamp"]
        with pytest.raises(SignatureVerificationError, match="Missing X-Timestamp"):
            verify_signature(payload, headers, secret=SECRET)

    def test_expired_timestamp_rejected(self) -> None:
        """A signature from 10 minutes ago is outside the default 5-min window."""
        payload = b'{"event":"event.created"}'
        old_ts = int(time.time()) - 600
        headers = {"X-Signature": _sign(payload, str(old_ts)), "X-Timestamp": str(old_ts)}
        with pytest.raises(SignatureVerificationError, match="tolerance"):
            verify_signature(payload, headers, secret=SECRET)

    def test_custom_tolerance_allows_older_timestamp(self) -> None:
        payload = b'{"event":"event.created"}'
        old_ts = int(time.time()) - 600
        headers = {"X-Signature": _sign(payload, str(old_ts)), "X-Timestamp": str(old_ts)}
        verify_signature(payload, headers, secret=SECRET, tolerance=3600)

    def test_future_timestamp_outside_tolerance_rejected(self) -> None:
        """Clock-skew windows work in both directions."""
        payload = b'{"event":"event.created"}'
        future_ts = int(time.time()) + 600
        headers = {"X-Signature": _sign(payload, str(future_ts)), "X-Timestamp": str(future_ts)}
        with pytest.raises(SignatureVerificationError, match="tolerance"):
            verify_signature(payload, headers, secret=SECRET)

    def test_malformed_timestamp_rejected(self) -> None:
        payload = b'{"event":"event.created"}'
        headers = {"X-Signature": _sign(payload, "nope"), "X-Timestamp": "nope"}
        with pytest.raises(SignatureVerificationError, match="not a valid integer"):
            verify_signature(payload, headers, secret=SECRET)

    def test_case_insensitive_header_lookup(self) -> None:
        payload = b'{"event":"event.created"}'
        ts = str(int(time.time()))
        headers = {"x-signature": _sign(payload, ts), "x-timestamp": ts}
        verify_signature(payload, headers, secret=SECRET)

    def test_headers_like_object_with_get(self) -> None:
        """Accepts httpx/starlette/werkzeug-style Headers objects."""
        import httpx

        payload = b'{"event":"event.created"}'
        ts = str(int(time.time()))
        headers = httpx.Headers([("X-Signature", _sign(payload, ts)), ("X-Timestamp", ts)])
        verify_signature(payload, headers, secret=SECRET)

    def test_empty_payload(self) -> None:
        payload = b""
        verify_signature(payload, _valid_headers(payload), secret=SECRET)

    def test_invalid_payload_type_raises(self) -> None:
        with pytest.raises(SignatureVerificationError, match="bytes or str"):
            verify_signature(12345, {}, secret=SECRET)  # type: ignore[arg-type]


class TestUnwrap:
    def test_returns_parsed_json_on_valid_signature(self) -> None:
        event_payload = {"event": {"id": "evt_1"}, "x": 1}
        payload = json.dumps(event_payload).encode("utf-8")
        result = unwrap(payload, _valid_headers(payload), secret=SECRET)
        assert result == {"type": "event.created", "data": event_payload}

    def test_accepts_string_payload(self) -> None:
        event_payload = {"event": {"id": "evt_1"}}
        payload_str = json.dumps(event_payload)
        payload_bytes = payload_str.encode("utf-8")
        result = unwrap(payload_str, _valid_headers(payload_bytes), secret=SECRET)
        assert result["type"] == "event.created"
        assert result["data"] == event_payload

    def test_requires_event_type_header(self) -> None:
        payload = b'{"event":{"id":"evt_1"}}'
        headers = _valid_headers(payload)
        del headers["X-Chronary-Event-Type"]
        with pytest.raises(SignatureVerificationError, match="X-Chronary-Event-Type"):
            unwrap(payload, headers, secret=SECRET)

    def test_raises_on_bad_signature(self) -> None:
        payload = b'{"type":"event.created"}'
        with pytest.raises(SignatureVerificationError):
            unwrap(payload, _valid_headers(payload), secret="wrong")

    def test_raises_on_invalid_json_with_valid_signature(self) -> None:
        payload = b"not json"
        with pytest.raises(ValueError):
            unwrap(payload, _valid_headers(payload), secret=SECRET)


class TestSecretRotation:
    """#594: during a rotation's grace window deliveries carry both headers."""

    OLD = "whsec_old"
    NEW = "whsec_new"

    def _rotated_headers(self, payload: bytes, *, ts: int | None = None) -> dict[str, str]:
        ts_str = str(ts if ts is not None else int(time.time()))
        return {
            "X-Signature": _sign(payload, ts_str, self.NEW),
            "X-Signature-Previous": _sign(payload, ts_str, self.OLD),
            "X-Timestamp": ts_str,
            "X-Chronary-Event-Type": "event.created",
        }

    def test_accepts_new_secret_via_x_signature(self) -> None:
        payload = b'{"event":{"id":"evt_1"}}'
        verify_signature(payload, self._rotated_headers(payload), secret=self.NEW)

    def test_accepts_old_secret_via_x_signature_previous(self) -> None:
        payload = b'{"event":{"id":"evt_1"}}'
        verify_signature(payload, self._rotated_headers(payload), secret=self.OLD)

    def test_previous_header_lookup_is_case_insensitive(self) -> None:
        payload = b'{"event":{"id":"evt_1"}}'
        lower = {k.lower(): v for k, v in self._rotated_headers(payload).items()}
        verify_signature(payload, lower, secret=self.OLD)

    def test_rejects_when_neither_header_matches(self) -> None:
        payload = b'{"event":{"id":"evt_1"}}'
        with pytest.raises(SignatureVerificationError, match="Signature mismatch"):
            verify_signature(payload, self._rotated_headers(payload), secret="whsec_other")

    def test_rejects_old_secret_after_the_window(self) -> None:
        payload = b'{"event":{"id":"evt_1"}}'
        headers = self._rotated_headers(payload)
        del headers["X-Signature-Previous"]
        with pytest.raises(SignatureVerificationError, match="Signature mismatch"):
            verify_signature(payload, headers, secret=self.OLD)

    def test_still_requires_x_signature(self) -> None:
        payload = b'{"event":{"id":"evt_1"}}'
        headers = self._rotated_headers(payload)
        del headers["X-Signature"]
        with pytest.raises(SignatureVerificationError, match="Missing X-Signature"):
            verify_signature(payload, headers, secret=self.OLD)

    def test_previous_signature_does_not_bypass_timestamp_check(self) -> None:
        payload = b'{"event":{"id":"evt_1"}}'
        headers = self._rotated_headers(payload, ts=int(time.time()) - 3600)
        with pytest.raises(SignatureVerificationError, match="tolerance"):
            verify_signature(payload, headers, secret=self.OLD)

    def test_unwrap_with_old_secret(self) -> None:
        payload = b'{"event":{"id":"evt_1"}}'
        event = unwrap(payload, self._rotated_headers(payload), secret=self.OLD)
        assert event["type"] == "event.created"
