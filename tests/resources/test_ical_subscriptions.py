from __future__ import annotations

import httpx
import respx

from chronary import AsyncChronary, Chronary, ICalSubscription
from chronary.pagination import AsyncPager, SyncPager

BASE = "https://api.chronary.ai"

ICAL_SUB_DATA = {
    "id": "ics_abc123",
    "agentId": "agt_abc123",
    "calendarId": "cal_abc123",
    "url": "https://example.com/calendar.ics",
    "label": "Team Calendar",
    "status": "active",
    "lastSyncedAt": "2026-01-15T10:30:00Z",
    "lastError": None,
    "createdAt": "2026-01-15T10:00:00Z",
}

LIST_RESPONSE = {
    "data": [ICAL_SUB_DATA],
    "total": 1,
    "limit": 50,
    "offset": 0,
}


# ---------------------------------------------------------------------------
# Sync tests
# ---------------------------------------------------------------------------


class TestSyncICalSubscriptions:
    @respx.mock
    def test_create(self) -> None:
        respx.post(f"{BASE}/v1/agents/agt_abc123/ical-subscriptions").mock(
            return_value=httpx.Response(201, json=ICAL_SUB_DATA)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            sub = client.ical_subscriptions.create(
                "agt_abc123",
                calendar_id="cal_abc123",
                url="https://example.com/calendar.ics",
                label="Team Calendar",
            )
            assert isinstance(sub, ICalSubscription)
            assert sub.id == "ics_abc123"
            assert sub.agent_id == "agt_abc123"
            assert sub.calendar_id == "cal_abc123"
            assert sub.label == "Team Calendar"

    @respx.mock
    def test_list(self) -> None:
        respx.get(f"{BASE}/v1/agents/agt_abc123/ical-subscriptions").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            pager = client.ical_subscriptions.list("agt_abc123")
            assert isinstance(pager, SyncPager)
            assert len(pager.data) == 1

    @respx.mock
    def test_get(self) -> None:
        respx.get(f"{BASE}/v1/ical-subscriptions/ics_abc123").mock(
            return_value=httpx.Response(200, json=ICAL_SUB_DATA)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            sub = client.ical_subscriptions.get("ics_abc123")
            assert sub.id == "ics_abc123"
            assert sub.status == "active"

    @respx.mock
    def test_update(self) -> None:
        updated = {**ICAL_SUB_DATA, "label": "New Label"}
        respx.patch(f"{BASE}/v1/ical-subscriptions/ics_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            sub = client.ical_subscriptions.update("ics_abc123", label="New Label")
            assert sub.label == "New Label"

    @respx.mock
    def test_delete(self) -> None:
        respx.delete(f"{BASE}/v1/ical-subscriptions/ics_abc123").mock(
            return_value=httpx.Response(204)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            result = client.ical_subscriptions.delete("ics_abc123")
            assert result is None

    @respx.mock
    def test_sync(self) -> None:
        respx.post(f"{BASE}/v1/ical-subscriptions/ics_abc123/sync").mock(
            return_value=httpx.Response(202, json={"status": "syncing"})
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            result = client.ical_subscriptions.sync("ics_abc123")
            assert result is None

    @respx.mock
    def test_request_id(self) -> None:
        respx.get(f"{BASE}/v1/ical-subscriptions/ics_abc123").mock(
            return_value=httpx.Response(
                200, json=ICAL_SUB_DATA, headers={"X-Request-Id": "req_ics_1"}
            )
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            sub = client.ical_subscriptions.get("ics_abc123")
            assert sub._request_id == "req_ics_1"


# ---------------------------------------------------------------------------
# Async tests
# ---------------------------------------------------------------------------


class TestAsyncICalSubscriptions:
    @respx.mock
    async def test_create(self) -> None:
        respx.post(f"{BASE}/v1/agents/agt_abc123/ical-subscriptions").mock(
            return_value=httpx.Response(201, json=ICAL_SUB_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            sub = await client.ical_subscriptions.create(
                "agt_abc123",
                calendar_id="cal_abc123",
                url="https://example.com/calendar.ics",
            )
            assert isinstance(sub, ICalSubscription)
            assert sub.id == "ics_abc123"

    @respx.mock
    async def test_list(self) -> None:
        respx.get(f"{BASE}/v1/agents/agt_abc123/ical-subscriptions").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            pager = await client.ical_subscriptions.list("agt_abc123")
            assert isinstance(pager, AsyncPager)
            assert len(pager.data) == 1

    @respx.mock
    async def test_get(self) -> None:
        respx.get(f"{BASE}/v1/ical-subscriptions/ics_abc123").mock(
            return_value=httpx.Response(200, json=ICAL_SUB_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            sub = await client.ical_subscriptions.get("ics_abc123")
            assert sub.id == "ics_abc123"

    @respx.mock
    async def test_update(self) -> None:
        updated = {**ICAL_SUB_DATA, "url": "https://new.example.com/cal.ics"}
        respx.patch(f"{BASE}/v1/ical-subscriptions/ics_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            sub = await client.ical_subscriptions.update(
                "ics_abc123", url="https://new.example.com/cal.ics"
            )
            assert sub.url == "https://new.example.com/cal.ics"

    @respx.mock
    async def test_delete(self) -> None:
        respx.delete(f"{BASE}/v1/ical-subscriptions/ics_abc123").mock(
            return_value=httpx.Response(204)
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            result = await client.ical_subscriptions.delete("ics_abc123")
            assert result is None

    @respx.mock
    async def test_sync(self) -> None:
        respx.post(f"{BASE}/v1/ical-subscriptions/ics_abc123/sync").mock(
            return_value=httpx.Response(202, json={"status": "syncing"})
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            result = await client.ical_subscriptions.sync("ics_abc123")
            assert result is None
