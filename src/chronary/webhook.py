r"""Webhook signature verification helpers.

Chronary signs each webhook delivery with HMAC-SHA256 and sends
``X-Signature-V2: sha256=<hex_digest>`` over the v2 message: these seven
fields joined by ``\n``::

    v2
    <X-Timestamp>            unix seconds as a decimal string
    <X-Delivery-Id>
    <X-Chronary-Event-Type>
    <1 when X-Chronary-Test is "1", else 0>
    <X-Chronary-Replay-Of, or empty>
    <raw body>

So the delivery id, event type, test flag and replay id are authenticated
along with the body (#2569). During a secret rotation's grace window it also
sends ``X-Signature-V2-Previous`` (same format, same message) signed with the
replaced secret. Verification passes when your secret matches either header,
so you can switch secrets at any point in the window.

The deprecated v1 ``X-Signature`` (over ``{timestamp}.{payload}`` only) is
still sent for hand-written verifiers, but this module never accepts it, so
stripping ``X-Signature-V2`` cannot downgrade the check.

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


def _v2_message(
    timestamp: str,
    delivery_id: str,
    event_type: str,
    test: bool,
    replay_of: str | None,
    payload: bytes,
) -> bytes:
    """The v2 signed message. No header field can hold an LF, so none can shift."""
    head = "\n".join(
        ["v2", timestamp, delivery_id, event_type, "1" if test else "0", replay_of or "", ""]
    )
    return head.encode("utf-8", "surrogateescape") + payload


def _compute_signature(secret: str, message: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _verify(
    payload: bytes | str,
    headers: Any,
    secret: str,
    tolerance: int,
) -> dict[str, Any]:
    """Verify the v2 signature; return the signed delivery metadata and body bytes."""
    if isinstance(payload, str):
        payload_bytes = payload.encode("utf-8")
    elif isinstance(payload, (bytes, bytearray)):
        payload_bytes = bytes(payload)
    else:
        raise SignatureVerificationError(
            f"payload must be bytes or str, got {type(payload).__name__}"
        )

    # X-Signature (v1) is never read: it does not cover the delivery id, event
    # type, test flag or replay id, so accepting it would let a stripped
    # X-Signature-V2 downgrade the check (#2569).
    signature = _get_header(headers, "X-Signature-V2")
    # Sent during a secret rotation's grace window, signed with the replaced secret.
    previous_signature = _get_header(headers, "X-Signature-V2-Previous")
    timestamp = _get_header(headers, "X-Timestamp")
    delivery_id = _get_header(headers, "X-Delivery-Id")
    event_type = _get_header(headers, "X-Chronary-Event-Type")
    test_header = _get_header(headers, "X-Chronary-Test")
    replay_of = _get_header(headers, "X-Chronary-Replay-Of")

    if not signature:
        raise SignatureVerificationError(
            "Missing X-Signature-V2 header. This SDK verifies only v2-signed "
            "deliveries; X-Signature (v1) is not accepted."
        )
    if not timestamp:
        raise SignatureVerificationError("Missing X-Timestamp header")
    if not delivery_id:
        raise SignatureVerificationError("Missing X-Delivery-Id header")
    if not event_type:
        raise SignatureVerificationError("Missing X-Chronary-Event-Type header")
    # Absent (or empty) means a live delivery; Chronary sends exactly "1" on a test.
    if test_header and test_header != "1":
        raise SignatureVerificationError("Invalid X-Chronary-Test header: expected 1 or no header")
    for value in (timestamp, delivery_id, event_type, replay_of or ""):
        if "\r" in value or "\n" in value:
            raise SignatureVerificationError("Webhook header contains CR or LF")

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

    test = test_header == "1"
    message = _v2_message(timestamp, delivery_id, event_type, test, replay_of, payload_bytes)
    expected = _compute_signature(secret, message).encode("ascii")
    # Both comparisons always run, in constant time. They compare bytes:
    # hmac.compare_digest raises TypeError on a str with non-ASCII characters,
    # which anyone can send in a header, so a junk signature crashed the
    # receiver instead of failing verification (#2724).
    matches_current = hmac.compare_digest(expected, _header_bytes(signature))
    matches_previous = bool(previous_signature) and hmac.compare_digest(
        expected, _header_bytes(previous_signature or "")
    )
    if not (matches_current or matches_previous):
        raise SignatureVerificationError("Signature mismatch")

    return {
        "type": event_type,
        "delivery_id": delivery_id,
        "test": test,
        "replay_of": replay_of or None,
        "payload": payload_bytes,
    }


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
        headers: A dict or Headers-like object containing
            ``X-Signature-V2``, ``X-Timestamp``, ``X-Delivery-Id`` and
            ``X-Chronary-Event-Type`` (plus ``X-Chronary-Test`` /
            ``X-Chronary-Replay-Of`` when Chronary sent them, and
            ``X-Signature-V2-Previous`` during a secret rotation). Lookup is
            case-insensitive.
        secret: The webhook signing secret (returned at webhook creation
            as ``whsec_...``).
        tolerance: Max seconds between the signed timestamp and now.
            Rejects replays older than this window. Default: 300 (5 min).

    Raises:
        SignatureVerificationError: On any failure — missing headers
            (including a v1-only delivery without ``X-Signature-V2``), stale
            timestamp, a metadata header that differs from what was signed,
            or signature mismatch. Uses constant-time comparison to prevent
            timing attacks.
    """
    _verify(payload, headers, secret, tolerance)


def _header_bytes(value: str | bytes) -> bytes:
    """A header value as bytes for a constant-time compare.

    ``surrogateescape`` keeps the lone surrogates some servers (aiohttp) use
    for undecodable header bytes from raising ``UnicodeEncodeError``.
    """
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    return str(value).encode("utf-8", "surrogateescape")


def unwrap(
    payload: bytes | str,
    headers: Any,
    *,
    secret: str,
    tolerance: int = 300,
) -> dict[str, Any]:
    """Verify a webhook and return its signed metadata with the parsed body.

    Combines ``verify_signature`` with JSON parsing so you can go from raw
    request to an event envelope in one call. Chronary sends the event type in
    ``X-Chronary-Event-Type`` and the raw event payload as the body; the v2
    signature covers both.

    Returns:
        A dict with ``type`` (``X-Chronary-Event-Type``), ``data`` (the parsed
        JSON payload), ``delivery_id`` (``X-Delivery-Id``, the same on every
        retry, so deduplicate on it), ``test`` (``True`` for a test send) and
        ``replay_of`` (the original delivery id on a replay, else ``None``).

    Raises:
        SignatureVerificationError: If signature verification fails.
        ValueError: If the payload is not valid JSON.
    """
    verified = _verify(payload, headers, secret, tolerance)
    return {
        "type": verified["type"],
        "data": json.loads(verified["payload"].decode("utf-8")),
        "delivery_id": verified["delivery_id"],
        "test": verified["test"],
        "replay_of": verified["replay_of"],
    }
