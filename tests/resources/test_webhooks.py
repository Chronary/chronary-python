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
    "url": "https://example.com/webhook",
    "events": ["event.created", "event.updated"],
    "active": True,
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
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            wh = client.webhooks.create(
                url="https://example.com/webhook",
                events=["event.created", "event.updated"],
            )
            assert isinstance(wh, Webhook)
            assert wh.id == "whk_abc123"
            assert wh.secret == "ws_test_secret_123"

    @respx.mock
    def test_list(self) -> None:
        respx.get(f"{BASE}/v1/webhooks").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            pager = client.webhooks.list()
            assert isinstance(pager, SyncPager)
            assert len(pager.data) == 1
            assert pager.data[0].secret is None  # Not present in list response

    @respx.mock
    def test_get(self) -> None:
        respx.get(f"{BASE}/v1/webhooks/whk_abc123").mock(
            return_value=httpx.Response(200, json=WEBHOOK_DATA)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            wh = client.webhooks.get("whk_abc123")
            assert wh.id == "whk_abc123"
            assert wh.url == "https://example.com/webhook"

    @respx.mock
    def test_update(self) -> None:
        updated = {**WEBHOOK_DATA, "active": False}
        respx.patch(f"{BASE}/v1/webhooks/whk_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            wh = client.webhooks.update("whk_abc123", active=False)
            assert wh.active is False

    @respx.mock
    def test_delete(self) -> None:
        respx.delete(f"{BASE}/v1/webhooks/whk_abc123").mock(
            return_value=httpx.Response(204)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            result = client.webhooks.delete("whk_abc123")
            assert result is None

    @respx.mock
    def test_request_id(self) -> None:
        respx.post(f"{BASE}/v1/webhooks").mock(
            return_value=httpx.Response(
                201, json=WEBHOOK_CREATE_DATA, headers={"X-Request-Id": "req_wh_1"}
            )
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
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
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
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
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            pager = await client.webhooks.list()
            assert isinstance(pager, AsyncPager)
            assert len(pager.data) == 1

    @respx.mock
    async def test_get(self) -> None:
        respx.get(f"{BASE}/v1/webhooks/whk_abc123").mock(
            return_value=httpx.Response(200, json=WEBHOOK_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            wh = await client.webhooks.get("whk_abc123")
            assert wh.id == "whk_abc123"

    @respx.mock
    async def test_update(self) -> None:
        updated = {**WEBHOOK_DATA, "events": ["event.deleted"]}
        respx.patch(f"{BASE}/v1/webhooks/whk_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            wh = await client.webhooks.update("whk_abc123", events=["event.deleted"])
            assert wh.events == ["event.deleted"]

    @respx.mock
    async def test_delete(self) -> None:
        respx.delete(f"{BASE}/v1/webhooks/whk_abc123").mock(
            return_value=httpx.Response(204)
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
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
                "url": "https://example.com/webhook",
                "events": [event_type],
                "active": True,
                "createdAt": "2026-01-15T10:30:00Z",
            }
        )
        assert wh.events == [event_type]

    def test_multiple_event_types_parse_together(self) -> None:
        """A webhook subscribed to many events should round-trip all of them."""
        wh = Webhook.model_validate(
            {
                "id": "whk_abc123",
                "url": "https://example.com/webhook",
                "events": list(_EXPECTED_EVENT_TYPES),
                "active": True,
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
                    "url": "https://example.com/webhook",
                    "events": ["event.totally_made_up"],
                    "active": True,
                    "createdAt": "2026-01-15T10:30:00Z",
                }
            )
