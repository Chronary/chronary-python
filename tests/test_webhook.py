"""Tests for chronary.webhook.verify_signature and unwrap.

Chronary signs HMAC over the v2 message (``v2``, timestamp, delivery id,
event type, test flag, replay-of id and the raw body, joined by LF) and sends
it as ``X-Signature-V2`` (#2569). The v1 ``X-Signature`` over
``{timestamp}.{payload}`` is still sent but never accepted by this SDK.
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


def _hmac(message: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def _sign_v1(payload: bytes, timestamp: str, secret: str = SECRET) -> str:
    return _hmac(f"{timestamp}.".encode() + payload, secret)


def _sign_v2(
    payload: bytes,
    timestamp: str,
    secret: str = SECRET,
    *,
    delivery_id: str = "whd_1",
    event_type: str = "event.created",
    test: bool = False,
    replay_of: str | None = None,
) -> str:
    head = "\n".join(
        ["v2", timestamp, delivery_id, event_type, "1" if test else "0", replay_of or "", ""]
    )
    return _hmac(head.encode("utf-8") + payload, secret)


def _valid_headers(
    payload: bytes,
    *,
    ts: int | str | None = None,
    secret: str = SECRET,
    delivery_id: str = "whd_1",
    event_type: str = "event.created",
    test: bool = False,
    replay_of: str | None = None,
) -> dict[str, str]:
    """The headers of one delivery, signed the way the API signs it."""
    ts_str = str(ts if ts is not None else int(time.time()))
    headers = {
        "X-Signature-V2": _sign_v2(
            payload,
            ts_str,
            secret,
            delivery_id=delivery_id,
            event_type=event_type,
            test=test,
            replay_of=replay_of,
        ),
        "X-Signature": _sign_v1(payload, ts_str, secret),
        "X-Timestamp": ts_str,
        "X-Delivery-Id": delivery_id,
        "X-Chronary-Event-Type": event_type,
    }
    if test:
        headers["X-Chronary-Test"] = "1"
    if replay_of:
        headers["X-Chronary-Replay-Of"] = replay_of
    return headers


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

    def test_missing_signature_header_even_with_valid_v1(self) -> None:
        payload = b'{"event":"event.created"}'
        headers = _valid_headers(payload)
        del headers["X-Signature-V2"]
        with pytest.raises(SignatureVerificationError, match="Missing X-Signature-V2"):
            verify_signature(payload, headers, secret=SECRET)

    @pytest.mark.parametrize("header", ["X-Timestamp", "X-Delivery-Id", "X-Chronary-Event-Type"])
    def test_missing_signed_header(self, header: str) -> None:
        payload = b'{"event":"event.created"}'
        headers = _valid_headers(payload)
        del headers[header]
        with pytest.raises(SignatureVerificationError, match=f"Missing {header}"):
            verify_signature(payload, headers, secret=SECRET)

    def test_expired_timestamp_rejected(self) -> None:
        """A signature from 10 minutes ago is outside the default 5-min window."""
        payload = b'{"event":"event.created"}'
        headers = _valid_headers(payload, ts=int(time.time()) - 600)
        with pytest.raises(SignatureVerificationError, match="tolerance"):
            verify_signature(payload, headers, secret=SECRET)

    def test_custom_tolerance_allows_older_timestamp(self) -> None:
        payload = b'{"event":"event.created"}'
        headers = _valid_headers(payload, ts=int(time.time()) - 600)
        verify_signature(payload, headers, secret=SECRET, tolerance=3600)

    def test_future_timestamp_outside_tolerance_rejected(self) -> None:
        """Clock-skew windows work in both directions."""
        payload = b'{"event":"event.created"}'
        headers = _valid_headers(payload, ts=int(time.time()) + 600)
        with pytest.raises(SignatureVerificationError, match="tolerance"):
            verify_signature(payload, headers, secret=SECRET)

    def test_malformed_timestamp_rejected(self) -> None:
        payload = b'{"event":"event.created"}'
        headers = _valid_headers(payload, ts="nope")
        with pytest.raises(SignatureVerificationError, match="not a valid integer"):
            verify_signature(payload, headers, secret=SECRET)

    def test_case_insensitive_header_lookup(self) -> None:
        payload = b'{"event":"event.created"}'
        headers = {k.lower(): v for k, v in _valid_headers(payload).items()}
        verify_signature(payload, headers, secret=SECRET)

    def test_headers_like_object_with_get(self) -> None:
        """Accepts httpx/starlette/werkzeug-style Headers objects."""
        import httpx

        payload = b'{"event":"event.created"}'
        headers = httpx.Headers(list(_valid_headers(payload, test=True).items()))
        verify_signature(payload, headers, secret=SECRET)

    def test_empty_payload(self) -> None:
        payload = b""
        verify_signature(payload, _valid_headers(payload), secret=SECRET)

    def test_invalid_payload_type_raises(self) -> None:
        with pytest.raises(SignatureVerificationError, match="bytes or str"):
            verify_signature(12345, {}, secret=SECRET)  # type: ignore[arg-type]


class TestSignedDeliveryMetadata:
    """BH-069 / #2569: the event type, delivery id, test flag and replay id
    are covered by X-Signature-V2, so a captured delivery cannot be re-sent
    with any of them changed."""

    PAYLOAD = b'{"calendar_id":"cal_1","event":{"id":"evt_1","title":"x"}}'

    def _rejects(self, headers: dict[str, str]) -> None:
        with pytest.raises(SignatureVerificationError):
            verify_signature(self.PAYLOAD, headers, secret=SECRET)
        with pytest.raises(SignatureVerificationError):
            unwrap(self.PAYLOAD, headers, secret=SECRET)

    def test_relabelled_event_type_rejected(self) -> None:
        headers = _valid_headers(self.PAYLOAD, delivery_id="whd_original")
        self._rejects({**headers, "X-Chronary-Event-Type": "event.updated"})

    def test_hold_relabel_rejected(self) -> None:
        body = b'{"calendar_id":"cal_1","event_id":"evt_1"}'
        headers = _valid_headers(body, event_type="event.hold_released")
        with pytest.raises(SignatureVerificationError, match="mismatch"):
            verify_signature(
                body, {**headers, "X-Chronary-Event-Type": "event.deleted"}, secret=SECRET
            )

    def test_swapped_delivery_id_rejected(self) -> None:
        headers = _valid_headers(self.PAYLOAD, delivery_id="whd_original")
        self._rejects({**headers, "X-Delivery-Id": "whd_attacker_fresh"})

    def test_stripped_test_flag_rejected(self) -> None:
        headers = _valid_headers(self.PAYLOAD, test=True)
        del headers["X-Chronary-Test"]
        self._rejects(headers)

    def test_added_test_flag_rejected(self) -> None:
        headers = _valid_headers(self.PAYLOAD)
        self._rejects({**headers, "X-Chronary-Test": "1"})
        with pytest.raises(SignatureVerificationError, match="Invalid X-Chronary-Test"):
            verify_signature(self.PAYLOAD, {**headers, "X-Chronary-Test": "true"}, secret=SECRET)

    def test_changed_added_or_stripped_replay_of_rejected(self) -> None:
        replay = _valid_headers(self.PAYLOAD, delivery_id="whd_r", replay_of="whd_original")
        self._rejects({**replay, "X-Chronary-Replay-Of": "whd_other"})
        stripped = dict(replay)
        del stripped["X-Chronary-Replay-Of"]
        self._rejects(stripped)
        live = _valid_headers(self.PAYLOAD)
        self._rejects({**live, "X-Chronary-Replay-Of": "whd_original"})

    def test_no_fallback_to_v1_when_v2_stripped(self) -> None:
        headers = _valid_headers(self.PAYLOAD)
        del headers["X-Signature-V2"]
        self._rejects(headers)
        self._rejects({**headers, "X-Chronary-Event-Type": "event.updated"})

    def test_v1_signature_in_v2_header_rejected(self) -> None:
        headers = _valid_headers(self.PAYLOAD)
        self._rejects({**headers, "X-Signature-V2": headers["X-Signature"]})

    def test_crlf_in_header_rejected(self) -> None:
        headers = _valid_headers(self.PAYLOAD)
        with pytest.raises(SignatureVerificationError, match="CR or LF"):
            verify_signature(
                self.PAYLOAD,
                {**headers, "X-Delivery-Id": "whd_1\nevent.created"},
                secret=SECRET,
            )

    def test_unwrap_returns_signed_metadata(self) -> None:
        headers = _valid_headers(self.PAYLOAD, delivery_id="whd_2", test=True, replay_of="whd_1")
        assert unwrap(self.PAYLOAD, headers, secret=SECRET) == {
            "type": "event.created",
            "data": json.loads(self.PAYLOAD),
            "delivery_id": "whd_2",
            "test": True,
            "replay_of": "whd_1",
        }

    @pytest.mark.parametrize(
        ("delivery_id", "test", "replay_of", "signature"),
        [
            (
                "whd_vector1",
                False,
                None,
                "sha256=5ee321bd30e58aef4e26fb8cb10850982d8d11531e767983737f346908a88560",
            ),
            (
                "whd_vector1",
                True,
                None,
                "sha256=d81393f416bf1894fb8ddd17eb2527fd74104cf57f9e5b1d5b7eeb6d2c00048d",
            ),
            (
                "whd_vector2",
                False,
                "whd_vector1",
                "sha256=cc34c8c295b86e898ce7675a34c9ca16ab1e843459ebcaa74d56dae5b8e0df88",
            ),
        ],
    )
    def test_shared_known_answer_vectors(
        self,
        monkeypatch: pytest.MonkeyPatch,
        delivery_id: str,
        test: bool,
        replay_of: str | None,
        signature: str,
    ) -> None:
        """The same vectors as the API and the TS and Go SDK tests."""
        body = b'{"calendar_id":"cal_1","event":{"id":"evt_1"}}'
        monkeypatch.setattr(time, "time", lambda: 1745784205.0)
        headers = _valid_headers(
            body,
            ts="1745784205",
            secret="whsec_v2_test_vector",
            delivery_id=delivery_id,
            test=test,
            replay_of=replay_of,
        )
        headers["X-Signature-V2"] = signature
        verify_signature(body, headers, secret="whsec_v2_test_vector")


class TestUnwrap:
    def test_returns_parsed_json_on_valid_signature(self) -> None:
        event_payload = {"event": {"id": "evt_1"}, "x": 1}
        payload = json.dumps(event_payload).encode("utf-8")
        result = unwrap(payload, _valid_headers(payload), secret=SECRET)
        assert result == {
            "type": "event.created",
            "data": event_payload,
            "delivery_id": "whd_1",
            "test": False,
            "replay_of": None,
        }

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
        current = _valid_headers(payload, ts=ts_str, secret=self.NEW)
        previous = _valid_headers(payload, ts=ts_str, secret=self.OLD)
        return {
            **current,
            "X-Signature-Previous": previous["X-Signature"],
            "X-Signature-V2-Previous": previous["X-Signature-V2"],
        }

    def test_accepts_new_secret_via_x_signature_v2(self) -> None:
        payload = b'{"event":{"id":"evt_1"}}'
        verify_signature(payload, self._rotated_headers(payload), secret=self.NEW)

    def test_accepts_old_secret_via_x_signature_v2_previous(self) -> None:
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
        del headers["X-Signature-V2-Previous"]
        # X-Signature-Previous (v1) is still there and valid, and is ignored.
        with pytest.raises(SignatureVerificationError, match="Signature mismatch"):
            verify_signature(payload, headers, secret=self.OLD)

    def test_still_requires_x_signature_v2(self) -> None:
        payload = b'{"event":{"id":"evt_1"}}'
        headers = self._rotated_headers(payload)
        del headers["X-Signature-V2"]
        with pytest.raises(SignatureVerificationError, match="Missing X-Signature-V2"):
            verify_signature(payload, headers, secret=self.OLD)

    def test_previous_twin_covers_the_event_type(self) -> None:
        payload = b'{"event":{"id":"evt_1"}}'
        headers = {**self._rotated_headers(payload), "X-Chronary-Event-Type": "event.updated"}
        with pytest.raises(SignatureVerificationError, match="Signature mismatch"):
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


class TestNonAsciiSignatureHeaders:
    """#2724: a non-ASCII signature header made hmac.compare_digest raise
    TypeError (a 500 in a receiver) instead of SignatureVerificationError."""

    PAYLOAD = b'{"event":{"id":"evt_1"}}'

    def _headers(self, signature: str, previous: str | None = None) -> dict[str, str]:
        headers = _valid_headers(self.PAYLOAD)
        headers["X-Signature-V2"] = signature
        if previous is not None:
            headers["X-Signature-V2-Previous"] = previous
        return headers

    def test_latin1_signature_is_a_mismatch(self) -> None:
        # WSGI / Starlette decode header bytes 0x80-0xFF as latin-1.
        with pytest.raises(SignatureVerificationError, match="Signature mismatch"):
            verify_signature(self.PAYLOAD, self._headers("sha256=éÿ"), secret=SECRET)

    def test_surrogate_signature_is_a_mismatch(self) -> None:
        # aiohttp hands undecodable header bytes over as lone surrogates.
        with pytest.raises(SignatureVerificationError, match="Signature mismatch"):
            verify_signature(self.PAYLOAD, self._headers("sha256=\udcff\udc80"), secret=SECRET)

    def test_junk_previous_next_to_valid_signature_is_accepted(self) -> None:
        good = _valid_headers(self.PAYLOAD)["X-Signature-V2"]
        verify_signature(self.PAYLOAD, self._headers(good, previous="é\udcff"), secret=SECRET)

    def test_junk_signature_next_to_valid_previous_is_accepted(self) -> None:
        good = _valid_headers(self.PAYLOAD)["X-Signature-V2"]
        verify_signature(self.PAYLOAD, self._headers("é", previous=good), secret=SECRET)

    def test_unwrap_raises_signature_error(self) -> None:
        with pytest.raises(SignatureVerificationError, match="Signature mismatch"):
            unwrap(self.PAYLOAD, self._headers("sha256=é"), secret=SECRET)
