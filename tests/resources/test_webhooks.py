from __future__ import annotations

import json

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
from chronary.resources.webhooks import (
    RotatedWebhookSecret,
    WebhookDeliveryDetail,
    WebhookReplaySent,
    WebhookTestSent,
)

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

DELIVERY_DETAIL = {
    "id": "whd_1",
    "subscription_id": "whk_abc123",
    "event_type": "event.created",
    "status": "failed",
    "attempts": 1,
    "max_attempts": 4,
    "last_attempt_at": "2026-01-15T10:30:00Z",
    "next_retry_at": None,
    "created_at": "2026-01-15T10:30:00Z",
    "last_response_status": 503,
    "last_error_code": "non_2xx",
    "last_duration_ms": 120,
    "payload": {"id": "evt_1"},
    "payload_redacted": False,
    "request_headers": {
        "content-type": "application/json",
        "x-delivery-id": "whd_1",
        "x-chronary-event-type": "event.created",
    },
    "attempt_log": [
        {
            "id": "wha_1",
            "attempt_number": 1,
            "started_at": "2026-01-15T10:30:00Z",
            "duration_ms": 120,
            "response_status": 503,
            "response_body": "unavailable",
            "error_code": "non_2xx",
        }
    ],
}

TEST_SENT = {
    "delivery_id": "whd_t",
    "webhook_id": "whk_abc123",
    "event_type": "event.created",
    "status": "pending",
    "is_test": True,
}

REPLAY_SENT = {
    "delivery_id": "whd_new",
    "webhook_id": "whk_abc123",
    "event_type": "event.created",
    "status": "pending",
    "replay_of_delivery_id": "whd_orig",
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

    @respx.mock
    def test_get_delivery(self) -> None:
        respx.get(f"{BASE}/v1/webhooks/whk_abc123/deliveries/whd_1").mock(
            return_value=httpx.Response(200, json=DELIVERY_DETAIL)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            d = client.webhooks.get_delivery("whk_abc123", "whd_1")
            assert isinstance(d, WebhookDeliveryDetail)
            assert d.max_attempts == 4
            assert d.last_error_code == "non_2xx"
            assert d.attempt_log[0].response_status == 503
            assert d.attempt_log[0].response_body == "unavailable"
            assert d.is_test is False

    @respx.mock
    def test_send_test(self) -> None:
        route = respx.post(f"{BASE}/v1/webhooks/whk_abc123/test").mock(
            return_value=httpx.Response(202, json=TEST_SENT)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            sent = client.webhooks.send_test("whk_abc123", event_type="event.created")
            assert isinstance(sent, WebhookTestSent)
            assert sent.delivery_id == "whd_t"
            assert sent.is_test is True
            assert json.loads(route.calls[0].request.content) == {"event_type": "event.created"}

    @respx.mock
    def test_replay_delivery(self) -> None:
        route = respx.post(f"{BASE}/v1/webhooks/whk_abc123/deliveries/whd_orig/replay").mock(
            return_value=httpx.Response(202, json=REPLAY_SENT)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            sent = client.webhooks.replay_delivery(
                "whk_abc123", "whd_orig", idempotency_key="replay-1"
            )
            assert isinstance(sent, WebhookReplaySent)
            assert sent.delivery_id == "whd_new"
            assert sent.replay_of_delivery_id == "whd_orig"
            request = route.calls[0].request
            assert request.content == b""
            assert request.headers["Idempotency-Key"] == "replay-1"

    @respx.mock
    def test_delivery_replay_link(self) -> None:
        respx.get(f"{BASE}/v1/webhooks/whk_abc123/deliveries/whd_new").mock(
            return_value=httpx.Response(
                200,
                json={
                    **DELIVERY_DETAIL,
                    "id": "whd_new",
                    "replay_of_delivery_id": "whd_orig",
                    "request_headers": {
                        "content-type": "application/json",
                        "x-delivery-id": "whd_new",
                        "x-chronary-event-type": "event.created",
                        "x-chronary-replay-of": "whd_orig",
                    },
                },
            )
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            d = client.webhooks.get_delivery("whk_abc123", "whd_new")
            assert d.replay_of_delivery_id == "whd_orig"
            assert d.request_headers["x-chronary-replay-of"] == "whd_orig"

    @respx.mock
    def test_rotate_secret(self) -> None:
        route = respx.post(f"{BASE}/v1/webhooks/whk_abc123/secret/rotate").mock(
            return_value=httpx.Response(
                200,
                json={
                    "webhook_id": "whk_abc123",
                    "secret": "whsec_new",
                    "previous_secret_expires_at": "2026-11-05T10:00:00Z",
                },
            )
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            rotated = client.webhooks.rotate_secret("whk_abc123", expire_old_in="1h")
            assert isinstance(rotated, RotatedWebhookSecret)
            assert rotated.secret == "whsec_new"
            assert rotated.previous_secret_expires_at is not None
            assert json.loads(route.calls[0].request.content) == {"expire_old_in": "1h"}

    @respx.mock
    def test_rotate_secret_default_body(self) -> None:
        route = respx.post(f"{BASE}/v1/webhooks/whk_abc123/secret/rotate").mock(
            return_value=httpx.Response(
                200,
                json={
                    "webhook_id": "whk_abc123",
                    "secret": "whsec_new",
                    "previous_secret_expires_at": None,
                },
            )
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            rotated = client.webhooks.rotate_secret("whk_abc123")
            assert rotated.previous_secret_expires_at is None
            assert json.loads(route.calls[0].request.content) == {}

    @respx.mock
    def test_webhook_previous_secret_expires_at(self) -> None:
        respx.get(f"{BASE}/v1/webhooks/whk_abc123").mock(
            return_value=httpx.Response(
                200, json={**WEBHOOK_DATA, "previousSecretExpiresAt": "2026-11-05T10:00:00Z"}
            )
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            wh = client.webhooks.get("whk_abc123")
            assert wh.previous_secret_expires_at is not None

    @respx.mock
    def test_webhook_deactivation_fields(self) -> None:
        respx.get(f"{BASE}/v1/webhooks/whk_abc123").mock(
            return_value=httpx.Response(
                200,
                json={
                    **WEBHOOK_DATA,
                    "active": False,
                    "deactivatedAt": "2026-01-15T10:30:00Z",
                    "deactivatedReason": "circuit_breaker",
                },
            )
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            wh = client.webhooks.get("whk_abc123")
            assert wh.deactivated_reason == "circuit_breaker"
            assert wh.deactivated_at is not None


# ---------------------------------------------------------------------------
# Async tests
# ---------------------------------------------------------------------------


class TestListDeliveriesFilters:
    """#1200: list filters, keyset cursor and the dropped status."""

    PAGE = {
        "data": [
            {
                "id": "whd_1",
                "subscription_id": "whk_abc123",
                "event_type": "event.created",
                "status": "dropped",
                "attempts": 0,
                "last_attempt_at": None,
                "next_retry_at": None,
                "created_at": "2026-04-18T10:00:00.000Z",
                "last_response_status": None,
                "last_error_code": "quota_exceeded",
                "last_duration_ms": None,
                "is_test": False,
            }
        ],
        "total": 3,
        "limit": 1,
        "offset": 0,
        "next_cursor": "WyJ4IiwieSJd",
        "has_more": True,
        "stats": {"pending": 0, "delivered": 1, "failed": 0, "dropped": 2},
    }

    @respx.mock
    def test_sync_sends_filters_and_reads_cursor(self) -> None:
        route = respx.get(f"{BASE}/v1/webhooks/whk_abc123/deliveries").mock(
            return_value=httpx.Response(200, json=self.PAGE)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            page = client.webhooks.list_deliveries(
                "whk_abc123",
                limit=1,
                status="dropped",
                event_type="event.",
                created_after="2026-04-18T00:00:00Z",
                created_before="2026-04-19T00:00:00Z",
                delivery_id="whd_1",
                is_test=False,
                cursor="abc",
            )
        params = dict(route.calls[0].request.url.params)
        assert params == {
            "limit": "1",
            "status": "dropped",
            "event_type": "event.",
            "created_after": "2026-04-18T00:00:00Z",
            "created_before": "2026-04-19T00:00:00Z",
            "delivery_id": "whd_1",
            "is_test": "false",
            "cursor": "abc",
        }
        assert page.next_cursor == "WyJ4IiwieSJd"
        assert page.has_more is True
        assert page.stats.dropped == 2
        assert page.data[0].status == "dropped"

    @respx.mock
    async def test_async_sends_filters(self) -> None:
        route = respx.get(f"{BASE}/v1/webhooks/whk_abc123/deliveries").mock(
            return_value=httpx.Response(200, json=self.PAGE)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            page = await client.webhooks.list_deliveries("whk_abc123", is_test=True, cursor="abc")
        params = dict(route.calls[0].request.url.params)
        assert params == {"is_test": "true", "cursor": "abc"}
        assert page.has_more is True

    @respx.mock
    def test_older_response_without_cursor_fields_still_parses(self) -> None:
        legacy = {k: v for k, v in self.PAGE.items() if k not in ("next_cursor", "has_more")}
        legacy["stats"] = {"pending": 0, "delivered": 1, "failed": 0}
        legacy["data"] = []
        respx.get(f"{BASE}/v1/webhooks/whk_abc123/deliveries").mock(
            return_value=httpx.Response(200, json=legacy)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            page = client.webhooks.list_deliveries("whk_abc123")
        assert page.next_cursor is None
        assert page.has_more is False
        assert page.stats.dropped == 0


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

    @respx.mock
    async def test_get_delivery(self) -> None:
        respx.get(f"{BASE}/v1/webhooks/whk_abc123/deliveries/whd_1").mock(
            return_value=httpx.Response(200, json=DELIVERY_DETAIL)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            d = await client.webhooks.get_delivery("whk_abc123", "whd_1")
            assert d.attempt_log[0].error_code == "non_2xx"
            assert d.payload_redacted is False

    @respx.mock
    async def test_rotate_secret(self) -> None:
        respx.post(f"{BASE}/v1/webhooks/whk_abc123/secret/rotate").mock(
            return_value=httpx.Response(
                200,
                json={
                    "webhook_id": "whk_abc123",
                    "secret": "whsec_new",
                    "previous_secret_expires_at": None,
                },
            )
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            rotated = await client.webhooks.rotate_secret("whk_abc123", expire_old_in="now")
            assert rotated.secret == "whsec_new"
            assert rotated.previous_secret_expires_at is None

    @respx.mock
    async def test_send_test(self) -> None:
        respx.post(f"{BASE}/v1/webhooks/whk_abc123/test").mock(
            return_value=httpx.Response(202, json=TEST_SENT)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            sent = await client.webhooks.send_test("whk_abc123", event_type="event.created")
            assert sent.status == "pending"
            assert sent.webhook_id == "whk_abc123"

    @respx.mock
    async def test_replay_delivery(self) -> None:
        respx.post(f"{BASE}/v1/webhooks/whk_abc123/deliveries/whd_orig/replay").mock(
            return_value=httpx.Response(202, json=REPLAY_SENT)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            sent = await client.webhooks.replay_delivery("whk_abc123", "whd_orig")
            assert sent.status == "pending"
            assert sent.replay_of_delivery_id == "whd_orig"


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
    "org.plan_changed",
    "calendar_connection.reauthorization_required",
    "usage.threshold_crossed",
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
    "org.plan_changed",
    "calendar_connection.reauthorization_required",
    "usage.threshold_crossed",
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
