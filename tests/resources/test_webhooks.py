from __future__ import annotations

import httpx
import pytest
import respx
from pydantic import ValidationError

from chronary import (
    WEBHOOK_EVENT_TYPES,
    AsyncChronary,
    Chronary,
    Webhook,
    WebhookEventType,
)
from chronary.pagination import AsyncPager, SyncPager

BASE = "https://api.chronary.ai"

WEBHOOK_DATA = {
    "id": "whk_abc123",
    "orgId": "org_abc123",
    "url": "https://example.com/webhook",
    "events": ["event.created", "event.updated"],
    "active": True,
    "consecutiveFailures": 0,
    "firstFailureAt": None,
    "createdAt": "2026-01-15T10:30:00Z",
}

WEBHOOK_CREATE_DATA = {
    **WEBHOOK_DATA,
    "secret": "ws_test_secret_123",
}

LIST_RESPONSE = {
    "data": [WEBHOOK_DATA],
    "total": 1,
    "limit": 20,
    "offset": 0,
}


# ---------------------------------------------------------------------------
# Sync tests
# ---------------------------------------------------------------------------


class TestSyncWebhooks:
    @respx.mock
    def test_create(self) -> None:
        respx.post(f"{BASE}/v1/webhooks").mock(
            return_value=httpx.Response(201, json=WEBHOOK_CREATE_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            wh = client.webhooks.create(
                url="https://example.com/webhook",
                events=["event.created", "event.updated"],
            )
            assert isinstance(wh, Webhook)
            assert wh.id == "whk_abc123"
            assert wh.org_id == "org_abc123"
            assert wh.secret == "ws_test_secret_123"
            assert wh.consecutive_failures == 0
            assert wh.first_failure_at is None

    @respx.mock
    def test_list(self) -> None:
        respx.get(f"{BASE}/v1/webhooks").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = client.webhooks.list()
            assert isinstance(pager, SyncPager)
            assert len(pager.data) == 1
            assert pager.data[0].secret is None  # Not present in list response

    @respx.mock
    def test_get(self) -> None:
        respx.get(f"{BASE}/v1/webhooks/whk_abc123").mock(
            return_value=httpx.Response(200, json=WEBHOOK_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            wh = client.webhooks.get("whk_abc123")
            assert wh.id == "whk_abc123"
            assert wh.url == "https://example.com/webhook"

    @respx.mock
    def test_update(self) -> None:
        updated = {**WEBHOOK_DATA, "active": False}
        respx.patch(f"{BASE}/v1/webhooks/whk_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            wh = client.webhooks.update("whk_abc123", active=False)
            assert wh.active is False

    @respx.mock
    def test_delete(self) -> None:
        respx.delete(f"{BASE}/v1/webhooks/whk_abc123").mock(
            return_value=httpx.Response(204)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.webhooks.delete("whk_abc123")
            assert result is None

    @respx.mock
    def test_request_id(self) -> None:
        respx.post(f"{BASE}/v1/webhooks").mock(
            return_value=httpx.Response(
                201, json=WEBHOOK_CREATE_DATA, headers={"X-Request-Id": "req_wh_1"}
            )
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            wh = client.webhooks.create(
                url="https://example.com/webhook",
                events=["event.created"],
            )
            assert wh._request_id == "req_wh_1"


# ---------------------------------------------------------------------------
# Async tests
# ---------------------------------------------------------------------------


class TestAsyncWebhooks:
    @respx.mock
    async def test_create(self) -> None:
        respx.post(f"{BASE}/v1/webhooks").mock(
            return_value=httpx.Response(201, json=WEBHOOK_CREATE_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            wh = await client.webhooks.create(
                url="https://example.com/webhook",
                events=["event.created", "event.updated"],
            )
            assert isinstance(wh, Webhook)
            assert wh.secret == "ws_test_secret_123"

    @respx.mock
    async def test_list(self) -> None:
        respx.get(f"{BASE}/v1/webhooks").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = await client.webhooks.list()
            assert isinstance(pager, AsyncPager)
            assert len(pager.data) == 1

    @respx.mock
    async def test_get(self) -> None:
        respx.get(f"{BASE}/v1/webhooks/whk_abc123").mock(
            return_value=httpx.Response(200, json=WEBHOOK_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            wh = await client.webhooks.get("whk_abc123")
            assert wh.id == "whk_abc123"

    @respx.mock
    async def test_update(self) -> None:
        updated = {**WEBHOOK_DATA, "events": ["event.deleted"]}
        respx.patch(f"{BASE}/v1/webhooks/whk_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            wh = await client.webhooks.update("whk_abc123", events=["event.deleted"])
            assert wh.events == ["event.deleted"]

    @respx.mock
    async def test_delete(self) -> None:
        respx.delete(f"{BASE}/v1/webhooks/whk_abc123").mock(
            return_value=httpx.Response(204)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = await client.webhooks.delete("whk_abc123")
            assert result is None


# ---------------------------------------------------------------------------
# Webhook event type literal
# ---------------------------------------------------------------------------

# Source of truth: packages/shared/src/schemas/webhooks.ts WEBHOOK_EVENT_TYPES.
# If this list drifts, surface-sync CI should catch it.
_EXPECTED_EVENT_TYPES = (
    "agent.created",
    "agent.updated",
    "event.created",
    "event.updated",
    "event.deleted",
    "event.started",
    "event.ended",
    "event.reminder",
    "event.hold_created",
    "event.hold_expired",
    "event.hold_released",
    "event.hold_confirmed",
    "proposal.created",
    "proposal.responded",
    "proposal.confirmed",
    "proposal.expired",
    "proposal.cancelled",
    "webhook.deactivated",
)


class TestWebhookEventType:
    def test_constant_matches_shared_package(self) -> None:
        """WEBHOOK_EVENT_TYPES must mirror the zod enum in packages/shared exactly."""
        assert WEBHOOK_EVENT_TYPES == _EXPECTED_EVENT_TYPES

    def test_constant_has_all_phase_1_types(self) -> None:
        """Phase 1 added 11 event types beyond the original 5 — guard against silent removal."""
        phase_1_additions = {
            "event.started",
            "event.ended",
            "event.hold_created",
            "event.hold_expired",
            "event.hold_released",
            "event.hold_confirmed",
            "proposal.created",
            "proposal.responded",
            "proposal.confirmed",
            "proposal.expired",
            "proposal.cancelled",
        }
        assert phase_1_additions.issubset(set(WEBHOOK_EVENT_TYPES))

    @pytest.mark.parametrize("event_type", _EXPECTED_EVENT_TYPES)
    def test_known_event_type_parses(self, event_type: WebhookEventType) -> None:
        """Every documented event type must parse cleanly on the Webhook response model."""
        wh = Webhook.model_validate(
            {
                "id": "whk_abc123",
                "orgId": "org_abc123",
                "url": "https://example.com/webhook",
                "events": [event_type],
                "active": True,
                "consecutiveFailures": 0,
                "firstFailureAt": None,
                "createdAt": "2026-01-15T10:30:00Z",
            }
        )
        assert wh.events == [event_type]

    def test_multiple_event_types_parse_together(self) -> None:
        """A webhook subscribed to many events should round-trip all of them."""
        wh = Webhook.model_validate(
            {
                "id": "whk_abc123",
                "orgId": "org_abc123",
                "url": "https://example.com/webhook",
                "events": list(_EXPECTED_EVENT_TYPES),
                "active": True,
                "consecutiveFailures": 0,
                "firstFailureAt": None,
                "createdAt": "2026-01-15T10:30:00Z",
            }
        )
        assert wh.events == list(_EXPECTED_EVENT_TYPES)

    def test_unknown_event_type_is_rejected(self) -> None:
        """Typos or server-side event types the SDK version doesn't know about must fail loudly."""
        with pytest.raises(ValidationError):
            Webhook.model_validate(
                {
                    "id": "whk_abc123",
                    "orgId": "org_abc123",
                    "url": "https://example.com/webhook",
                    "events": ["event.totally_made_up"],
                    "active": True,
                    "consecutiveFailures": 0,
                    "createdAt": "2026-01-15T10:30:00Z",
                }
            )


# Parity check vs canonical list in packages/shared/src/schemas/webhooks.ts.
# Any drift here means the TS source of truth added an event type and the
# Python literal is silently rejecting it. Update both when adding new events.
_CANONICAL_EVENT_TYPES = (
    "agent.created",
    "agent.updated",
    "event.created",
    "event.updated",
    "event.deleted",
    "event.started",
    "event.ended",
    "event.reminder",
    "event.hold_created",
    "event.hold_expired",
    "event.hold_released",
    "event.hold_confirmed",
    "proposal.created",
    "proposal.responded",
    "proposal.confirmed",
    "proposal.expired",
    "proposal.cancelled",
    "webhook.deactivated",
)


class TestWebhookEventTypeParity:
    @pytest.mark.parametrize("event_type", _CANONICAL_EVENT_TYPES)
    def test_every_canonical_event_type_is_in_python_literal(self, event_type: str) -> None:
        assert event_type in WEBHOOK_EVENT_TYPES, (
            f"{event_type!r} is in packages/shared/src/schemas/webhooks.ts but missing from "
            f"the Python SDK WebhookEventType literal — parity drift"
        )

    def test_python_literal_matches_canonical_count(self) -> None:
        assert len(WEBHOOK_EVENT_TYPES) == len(_CANONICAL_EVENT_TYPES), (
            f"Python WEBHOOK_EVENT_TYPES has {len(WEBHOOK_EVENT_TYPES)} entries, "
            f"canonical has {len(_CANONICAL_EVENT_TYPES)} — one of them is stale"
        )


class TestClientWebhooksVerifyDelegation:
    """client.webhooks.verify_signature and .unwrap delegate to chronary.webhook.*.

    Full crypto coverage is in tests/test_webhook.py. These tests just prove
    the resource-nested methods exist and route correctly.
    """

    def _sign(self, payload: bytes, timestamp: str, secret: str) -> str:
        import hashlib
        import hmac

        message = f"{timestamp}.".encode("utf-8") + payload
        return "sha256=" + hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

    def test_verify_signature_accepts_valid_webhook(self) -> None:
        import time

        secret = "whsec_test"
        payload = b'{"event":{"id":"evt_1"}}'
        ts = str(int(time.time()))
        headers = {
            "X-Signature": self._sign(payload, ts, secret),
            "X-Timestamp": ts,
            "X-Chronary-Event-Type": "event.created",
        }

        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            # Returns None on success; raises on failure.
            client.webhooks.verify_signature(payload, headers, secret=secret)

    def test_verify_signature_raises_on_tampered(self) -> None:
        import time

        from chronary import SignatureVerificationError

        secret = "whsec_test"
        payload = b'{"event":{"id":"evt_1"}}'
        ts = str(int(time.time()))
        headers = {
            "X-Signature": self._sign(payload, ts, secret),
            "X-Timestamp": ts,
            "X-Chronary-Event-Type": "event.created",
        }

        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            with pytest.raises(SignatureVerificationError):
                client.webhooks.verify_signature(
                    b'{"event":{"id":"evt_2"}}', headers, secret=secret
                )

    def test_unwrap_returns_parsed_event(self) -> None:
        import time

        secret = "whsec_test"
        event_body = {"event": {"id": "evt_1"}, "x": 1}
        import json

        payload = json.dumps(event_body).encode("utf-8")
        ts = str(int(time.time()))
        headers = {
            "X-Signature": self._sign(payload, ts, secret),
            "X-Timestamp": ts,
            "X-Chronary-Event-Type": "event.created",
        }

        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.webhooks.unwrap(payload, headers, secret=secret)
            assert result == {"type": "event.created", "data": event_body}

    async def test_async_client_exposes_same_methods(self) -> None:
        import time

        secret = "whsec_test"
        payload = b'{"event":{"id":"evt_1"}}'
        ts = str(int(time.time()))
        headers = {
            "X-Signature": self._sign(payload, ts, secret),
            "X-Timestamp": ts,
            "X-Chronary-Event-Type": "event.created",
        }

        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            # Methods are @staticmethod so they work on both sync + async
            # resources without awaiting.
            client.webhooks.verify_signature(payload, headers, secret=secret)
