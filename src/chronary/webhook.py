"""Webhook signature verification helper.

Usage::

    from chronary.webhook import verify_signature

    is_valid = verify_signature(
        payload=request.body,
        signature=request.headers["X-Chronary-Signature"],
        secret=webhook_secret,
    )
"""

from __future__ import annotations

import hashlib
import hmac


def verify_signature(payload: bytes | str, signature: str, secret: str) -> bool:
    """Verify an incoming webhook request's HMAC-SHA256 signature.

    The Chronary API signs webhook payloads with the webhook's secret using
    HMAC-SHA256 and sends the result in the ``X-Chronary-Signature`` header
    in the format ``sha256=<hex_digest>``.

    This function uses constant-time comparison to prevent timing attacks.

    Args:
        payload: The raw request body (bytes or UTF-8 string).
        signature: The value of the ``X-Chronary-Signature`` header.
        secret: The webhook signing secret (returned at webhook creation).

    Returns:
        ``True`` if the signature is valid, ``False`` otherwise.
    """
    if isinstance(payload, str):
        payload = payload.encode("utf-8")

    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    expected_sig = f"sha256={expected}"
    return hmac.compare_digest(expected_sig, signature)
