from __future__ import annotations

import httpx
import respx

from chronary import (
    AsyncChronary,
    AvailabilityRules,
    Calendar,
    CalendarContext,
    Chronary,
)
from chronary.pagination import AsyncPager, SyncPager

BASE = "https://api.chronary.ai"

CALENDAR_DATA = {
    "id": "cal_abc123",
    "name": "Sales Agent Calendar",
    "timezone": "America/New_York",
    "agentId": "agt_abc123",
    "metadata": {},
    "ical_url": "https://ical.chronary.ai/ical/TOKEN.ics",
    "createdAt": "2026-01-15T10:30:00Z",
    "updatedAt": "2026-01-15T10:30:00Z",
}

LIST_RESPONSE = {
    "data": [CALENDAR_DATA],
    "total": 1,
    "limit": 50,
    "offset": 0,
}


# ---------------------------------------------------------------------------
# Sync tests
# ---------------------------------------------------------------------------


class TestSyncCalendars:
    @respx.mock
    def test_create(self) -> None:
        respx.post(f"{BASE}/v1/calendars").mock(
            return_value=httpx.Response(201, json=CALENDAR_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            cal = client.calendars.create(name="Sales Agent Calendar", timezone="America/New_York")
            assert isinstance(cal, Calendar)
            assert cal.id == "cal_abc123"
            assert cal.timezone == "America/New_York"
            assert cal.ical_url == "https://ical.chronary.ai/ical/TOKEN.ics"

    @respx.mock
    def test_list(self) -> None:
        respx.get(f"{BASE}/v1/calendars").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = client.calendars.list()
            assert isinstance(pager, SyncPager)
            assert len(pager.data) == 1
            assert pager.data[0].id == "cal_abc123"

    @respx.mock
    def test_get(self) -> None:
        respx.get(f"{BASE}/v1/calendars/cal_abc123").mock(
            return_value=httpx.Response(200, json=CALENDAR_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            cal = client.calendars.get("cal_abc123")
            assert cal.id == "cal_abc123"
            assert cal.agent_id == "agt_abc123"

    @respx.mock
    def test_update(self) -> None:
        updated = {**CALENDAR_DATA, "name": "Renamed"}
        respx.patch(f"{BASE}/v1/calendars/cal_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            cal = client.calendars.update("cal_abc123", name="Renamed")
            assert cal.name == "Renamed"

    @respx.mock
    def test_delete(self) -> None:
        respx.delete(f"{BASE}/v1/calendars/cal_abc123").mock(
            return_value=httpx.Response(204)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.calendars.delete("cal_abc123")
            assert result is None

    @respx.mock
    def test_request_id(self) -> None:
        respx.get(f"{BASE}/v1/calendars/cal_abc123").mock(
            return_value=httpx.Response(
                200, json=CALENDAR_DATA, headers={"X-Request-Id": "req_cal_1"}
            )
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            cal = client.calendars.get("cal_abc123")
            assert cal._request_id == "req_cal_1"

    @respx.mock
    def test_get_context(self) -> None:
        respx.get(f"{BASE}/v1/calendars/cal_abc123/context").mock(
            return_value=httpx.Response(
                200,
                json={
                    "calendar_id": "cal_abc123",
                    "now": "2026-04-16T12:00:00Z",
                    "agent_status": "idle",
                    "current_event": None,
                    "next_event": None,
                    "recent_events": [],
                    "upcoming": [],
                },
            )
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            ctx = client.calendars.get_context("cal_abc123")
            assert isinstance(ctx, CalendarContext)
            assert ctx.calendar_id == "cal_abc123"
            assert ctx.agent_status == "idle"

    @respx.mock
    def test_set_availability_rules(self) -> None:
        rules = {
            "id": "rul_1",
            "calendar_id": "cal_abc123",
            "buffer_before_minutes": 10,
            "buffer_after_minutes": 15,
            "working_hours": None,
            "timezone": "UTC",
            "created_at": "2026-04-16T12:00:00Z",
            "updated_at": "2026-04-16T12:00:00Z",
        }
        respx.put(f"{BASE}/v1/calendars/cal_abc123/availability-rules").mock(
            return_value=httpx.Response(200, json=rules)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.calendars.set_availability_rules(
                "cal_abc123", buffer_before_minutes=10, buffer_after_minutes=15
            )
            assert isinstance(result, AvailabilityRules)
            assert result.buffer_before_minutes == 10

    @respx.mock
    def test_get_availability_rules(self) -> None:
        rules = {
            "id": "rul_1",
            "calendar_id": "cal_abc123",
            "buffer_before_minutes": 0,
            "buffer_after_minutes": 0,
            "working_hours": None,
            "timezone": "UTC",
            "created_at": "2026-04-16T12:00:00Z",
            "updated_at": "2026-04-16T12:00:00Z",
        }
        respx.get(f"{BASE}/v1/calendars/cal_abc123/availability-rules").mock(
            return_value=httpx.Response(200, json=rules)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.calendars.get_availability_rules("cal_abc123")
            assert result.id == "rul_1"

    @respx.mock
    def test_delete_availability_rules(self) -> None:
        respx.delete(f"{BASE}/v1/calendars/cal_abc123/availability-rules").mock(
            return_value=httpx.Response(204)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.calendars.delete_availability_rules("cal_abc123")
            assert result is None


# ---------------------------------------------------------------------------
# Agent-scoped sync tests
# ---------------------------------------------------------------------------


class TestSyncAgentCalendars:
    @respx.mock
    def test_create(self) -> None:
        respx.post(f"{BASE}/v1/agents/agt_abc123/calendars").mock(
            return_value=httpx.Response(201, json=CALENDAR_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            cal = client.agents.calendars.create(
                "agt_abc123", name="Sales Agent Calendar", timezone="America/New_York"
            )
            assert isinstance(cal, Calendar)
            assert cal.id == "cal_abc123"

    @respx.mock
    def test_list(self) -> None:
        respx.get(f"{BASE}/v1/agents/agt_abc123/calendars").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = client.agents.calendars.list("agt_abc123")
            assert isinstance(pager, SyncPager)
            assert len(pager.data) == 1


# ---------------------------------------------------------------------------
# Async tests
# ---------------------------------------------------------------------------


class TestAsyncCalendars:
    @respx.mock
    async def test_create(self) -> None:
        respx.post(f"{BASE}/v1/calendars").mock(
            return_value=httpx.Response(201, json=CALENDAR_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            cal = await client.calendars.create(
                name="Sales Agent Calendar", timezone="America/New_York"
            )
            assert isinstance(cal, Calendar)
            assert cal.id == "cal_abc123"

    @respx.mock
    async def test_list(self) -> None:
        respx.get(f"{BASE}/v1/calendars").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = await client.calendars.list()
            assert isinstance(pager, AsyncPager)
            assert len(pager.data) == 1

    @respx.mock
    async def test_get(self) -> None:
        respx.get(f"{BASE}/v1/calendars/cal_abc123").mock(
            return_value=httpx.Response(200, json=CALENDAR_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            cal = await client.calendars.get("cal_abc123")
            assert cal.id == "cal_abc123"

    @respx.mock
    async def test_update(self) -> None:
        updated = {**CALENDAR_DATA, "name": "Renamed"}
        respx.patch(f"{BASE}/v1/calendars/cal_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            cal = await client.calendars.update("cal_abc123", name="Renamed")
            assert cal.name == "Renamed"

    @respx.mock
    async def test_delete(self) -> None:
        respx.delete(f"{BASE}/v1/calendars/cal_abc123").mock(
            return_value=httpx.Response(204)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = await client.calendars.delete("cal_abc123")
            assert result is None


class TestAsyncAgentCalendars:
    @respx.mock
    async def test_create(self) -> None:
        respx.post(f"{BASE}/v1/agents/agt_abc123/calendars").mock(
            return_value=httpx.Response(201, json=CALENDAR_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            cal = await client.agents.calendars.create(
                "agt_abc123", name="Sales Agent Calendar", timezone="America/New_York"
            )
            assert isinstance(cal, Calendar)

    @respx.mock
    async def test_list(self) -> None:
        respx.get(f"{BASE}/v1/agents/agt_abc123/calendars").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = await client.agents.calendars.list("agt_abc123")
            assert isinstance(pager, AsyncPager)
            assert len(pager.data) == 1
