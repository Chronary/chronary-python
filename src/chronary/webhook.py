"""Webhook signature verification helpers.

Chronary signs each webhook delivery with HMAC-SHA256 over
``{timestamp}.{payload}`` (Stripe-style) and sends two headers:

- ``X-Timestamp`` — unix seconds as a decimal string
- ``X-Signature`` — ``sha256=<hex_digest>``

Both ``verify_signature`` and ``unwrap`` accept either a ``dict`` of
header name → value or an object with a ``.get(name)`` method (e.g.
``http.client.HTTPMessage``, ``starlette.datastructures.Headers``).
Header lookups are case-insensitive.

Usage::

    from chronary.webhook import verify_signature, unwrap

    verify_signature(payload=request.body, headers=request.headers, secret=secret)

    event = unwrap(payload=request.body, headers=request.headers, secret=secret)
    if event["type"] == "event.created":
        ...

You can also call these as methods on the client: ``client.webhooks.verify_signature(...)``
and ``client.webhooks.unwrap(...)``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Mapping


class SignatureVerificationError(Exception):
    """Raised when webhook signature verification fails.

    Covers every failure mode: missing/malformed headers, timestamp outside
    tolerance window (replay attack defense), and signature mismatch.
    """


def _get_header(headers: Any, name: str) -> str | None:
    """Case-insensitive header lookup tolerant of dicts and Headers-like objects."""
    if headers is None:
        return None

    # Headers-like: ``.get(name)``
    if hasattr(headers, "get") and not isinstance(headers, Mapping):
        # Most Headers-like objects (httpx, starlette, werkzeug) are
        # case-insensitive out of the box.
        value = headers.get(name)
        if value is not None:
            return str(value)
        return headers.get(name.lower()) if name != name.lower() else None

    if isinstance(headers, Mapping):
        # Try the exact key first, then common case variants.
        for key in (name, name.lower(), name.upper(), name.title()):
            if key in headers:
                return str(headers[key])
        # Fall back to a linear scan — O(n) but n is tiny for HTTP headers.
        target = name.lower()
        for key, value in headers.items():
            if isinstance(key, str) and key.lower() == target:
                return str(value)
        return None

    return None


def _compute_signature(secret: str, timestamp: str, payload: bytes) -> str:
    message = f"{timestamp}.".encode("utf-8") + payload
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(
    payload: bytes | str,
    headers: Any,
    *,
    secret: str,
    tolerance: int = 300,
) -> None:
    """Verify an incoming Chronary webhook's HMAC-SHA256 signature.

    Args:
        payload: The raw request body (bytes or UTF-8 string). Pass the
            exact bytes you received — do not re-serialize JSON.
        headers: A dict or Headers-like object containing ``X-Signature``
            and ``X-Timestamp``. Lookup is case-insensitive.
        secret: The webhook signing secret (returned at webhook creation
            as ``whsec_...``).
        tolerance: Max seconds between the signed timestamp and now.
            Rejects replays older than this window. Default: 300 (5 min).

    Raises:
        SignatureVerificationError: On any failure — missing headers,
            stale timestamp, or signature mismatch. Uses constant-time
            comparison to prevent timing attacks.
    """
    if isinstance(payload, str):
        payload_bytes = payload.encode("utf-8")
    elif isinstance(payload, (bytes, bytearray)):
        payload_bytes = bytes(payload)
    else:
        raise SignatureVerificationError(
            f"payload must be bytes or str, got {type(payload).__name__}"
        )

    signature = _get_header(headers, "X-Signature")
    timestamp = _get_header(headers, "X-Timestamp")

    if not signature:
        raise SignatureVerificationError("Missing X-Signature header")
    if not timestamp:
        raise SignatureVerificationError("Missing X-Timestamp header")

    try:
        ts_seconds = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise SignatureVerificationError(
            f"X-Timestamp header is not a valid integer: {timestamp!r}"
        ) from exc

    now_seconds = int(time.time())
    if abs(now_seconds - ts_seconds) > tolerance:
        raise SignatureVerificationError(
            f"Webhook timestamp {ts_seconds} outside tolerance window of {tolerance}s "
            f"(now {now_seconds})"
        )

    expected = _compute_signature(secret, timestamp, payload_bytes)
    if not hmac.compare_digest(expected, signature):
        raise SignatureVerificationError("Signature mismatch")


def unwrap(
    payload: bytes | str,
    headers: Any,
    *,
    secret: str,
    tolerance: int = 300,
) -> dict[str, Any]:
    """Verify a webhook and return ``{"type": event_type, "data": payload}``.

    Combines ``verify_signature`` with JSON parsing so you can go from raw
    request to an event envelope in one call. Chronary sends the event type in
    ``X-Chronary-Event-Type`` and the raw event payload as the body.

    Returns:
        A dict with ``type`` from the header and ``data`` containing the parsed
        JSON payload.

    Raises:
        SignatureVerificationError: If signature verification fails.
        ValueError: If the payload is not valid JSON.
    """
    verify_signature(payload, headers, secret=secret, tolerance=tolerance)

    event_type = _get_header(headers, "X-Chronary-Event-Type")
    if not event_type:
        raise SignatureVerificationError("Missing X-Chronary-Event-Type header")

    if isinstance(payload, (bytes, bytearray)):
        payload_str = bytes(payload).decode("utf-8")
    else:
        payload_str = payload

    return {"type": event_type, "data": json.loads(payload_str)}
