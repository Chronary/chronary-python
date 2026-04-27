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
    return {"X-Signature": _sign(payload, ts_str), "X-Timestamp": ts_str}


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
        event = {"id": "evt_1", "type": "event.created", "data": {"x": 1}}
        payload = json.dumps(event).encode("utf-8")
        result = unwrap(payload, _valid_headers(payload), secret=SECRET)
        assert result == event

    def test_accepts_string_payload(self) -> None:
        event = {"id": "evt_1", "type": "event.created"}
        payload_str = json.dumps(event)
        payload_bytes = payload_str.encode("utf-8")
        result = unwrap(payload_str, _valid_headers(payload_bytes), secret=SECRET)
        assert result["type"] == "event.created"

    def test_raises_on_bad_signature(self) -> None:
        payload = b'{"type":"event.created"}'
        with pytest.raises(SignatureVerificationError):
            unwrap(payload, _valid_headers(payload), secret="wrong")

    def test_raises_on_invalid_json_with_valid_signature(self) -> None:
        payload = b"not json"
        with pytest.raises(ValueError):
            unwrap(payload, _valid_headers(payload), secret=SECRET)
