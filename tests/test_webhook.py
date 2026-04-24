from __future__ import annotations

import hashlib
import hmac

from chronary.webhook import verify_signature


class TestVerifySignature:
    def test_valid_signature(self) -> None:
        payload = b'{"event":"event.created","data":{}}'
        secret = "ws_test_secret_123"
        digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        signature = f"sha256={digest}"

        assert verify_signature(payload, signature, secret) is True

    def test_invalid_signature(self) -> None:
        payload = b'{"event":"event.created","data":{}}'
        secret = "ws_test_secret_123"
        assert verify_signature(payload, "sha256=badhex", secret) is False

    def test_tampered_payload(self) -> None:
        payload = b'{"event":"event.created","data":{}}'
        secret = "ws_test_secret_123"
        digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        signature = f"sha256={digest}"

        tampered = b'{"event":"event.deleted","data":{}}'
        assert verify_signature(tampered, signature, secret) is False

    def test_wrong_secret(self) -> None:
        payload = b'{"event":"event.created","data":{}}'
        secret = "ws_test_secret_123"
        digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        signature = f"sha256={digest}"

        assert verify_signature(payload, signature, "wrong_secret") is False

    def test_string_payload(self) -> None:
        """String payloads should be auto-encoded to UTF-8."""
        payload_str = '{"event":"event.created","data":{}}'
        payload_bytes = payload_str.encode("utf-8")
        secret = "ws_test_secret_123"
        digest = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
        signature = f"sha256={digest}"

        assert verify_signature(payload_str, signature, secret) is True

    def test_empty_payload(self) -> None:
        payload = b""
        secret = "ws_test_secret_123"
        digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        signature = f"sha256={digest}"

        assert verify_signature(payload, signature, secret) is True

    def test_missing_prefix(self) -> None:
        """Signature without sha256= prefix should fail."""
        payload = b'{"event":"event.created"}'
        secret = "ws_test_secret_123"
        digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        # Pass raw hex without prefix
        assert verify_signature(payload, digest, secret) is False
