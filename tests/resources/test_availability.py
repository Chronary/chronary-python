from __future__ import annotations

import httpx
import respx

from chronary import (
    AgentAvailabilityResponse,
    AsyncChronary,
    CalendarAvailabilityResponse,
    Chronary,
    TimeSlot,
)

BASE = "https://api.chronary.ai"

HEALTH = {
    "availability_state": "complete",
    "sources": {"chronary": "current", "external": "current", "last_synced_at": None},
    "warnings": [],
}

AGENT_AVAIL_DATA = {
    **HEALTH,
    "agents": ["agt_abc123"],
    "slots": [
        {"start": "2026-03-28T10:00:00Z", "end": "2026-03-28T10:30:00Z"},
        {"start": "2026-03-28T14:00:00Z", "end": "2026-03-28T14:30:00Z"},
    ],
}

AGENT_AVAIL_WITH_BUSY = {
    **AGENT_AVAIL_DATA,
    "per_agent_busy": {
        "agt_abc123": [
            {
                "start": "2026-03-28T09:00:00Z",
                "end": "2026-03-28T10:00:00Z",
                "calendar_id": "cal_abc123",
            }
        ]
    },
}

CALENDAR_AVAIL_DATA = {
    **HEALTH,
    "calendar_id": "cal_abc123",
    "slots": [
        {"start": "2026-03-28T10:00:00Z", "end": "2026-03-28T10:30:00Z"},
    ],
}

CALENDAR_AVAIL_WITH_BUSY = {
    **CALENDAR_AVAIL_DATA,
    "busy": [
        {"start": "2026-03-28T09:00:00Z", "end": "2026-03-28T10:00:00Z"},
    ],
}

CROSS_AVAIL_DATA = {
    **HEALTH,
    "agents": ["agt_1", "agt_2"],
    "slots": [
        {"start": "2026-03-28T14:00:00Z", "end": "2026-03-28T14:30:00Z"},
    ],
}


# ---------------------------------------------------------------------------
# Sync tests
# ---------------------------------------------------------------------------


class TestSyncAvailability:
    @respx.mock
    def test_get_agent(self) -> None:
        route = respx.get(f"{BASE}/v1/agents/agt_abc123/availability").mock(
            return_value=httpx.Response(200, json=AGENT_AVAIL_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.availability.get(
                "agt_abc123",
                start="2026-03-28T09:00:00Z",
                end="2026-03-28T17:00:00Z",
                allow_stale=True,
            )
            assert isinstance(result, AgentAvailabilityResponse)
            assert result.agents == ["agt_abc123"]
            assert len(result.slots) == 2
            assert isinstance(result.slots[0], TimeSlot)
            assert result.per_agent_busy is None
            assert result.availability_state == "complete"
            assert route.calls.last.request.url.params.get("allow_stale") == "true"

    @respx.mock
    def test_get_agent_with_busy(self) -> None:
        respx.get(f"{BASE}/v1/agents/agt_abc123/availability").mock(
            return_value=httpx.Response(200, json=AGENT_AVAIL_WITH_BUSY)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.availability.get(
                "agt_abc123",
                start="2026-03-28T09:00:00Z",
                end="2026-03-28T17:00:00Z",
                include_busy=True,
            )
            assert result.per_agent_busy is not None
            assert "agt_abc123" in result.per_agent_busy
            assert result.per_agent_busy["agt_abc123"][0].calendar_id == "cal_abc123"

    @respx.mock
    def test_get_calendar(self) -> None:
        respx.get(f"{BASE}/v1/calendars/cal_abc123/availability").mock(
            return_value=httpx.Response(200, json=CALENDAR_AVAIL_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.availability.get_calendar(
                "cal_abc123",
                start="2026-03-28T09:00:00Z",
                end="2026-03-28T17:00:00Z",
            )
            assert isinstance(result, CalendarAvailabilityResponse)
            assert result.calendar_id == "cal_abc123"
            assert len(result.slots) == 1
            assert result.busy is None

    @respx.mock
    def test_get_calendar_with_busy(self) -> None:
        respx.get(f"{BASE}/v1/calendars/cal_abc123/availability").mock(
            return_value=httpx.Response(200, json=CALENDAR_AVAIL_WITH_BUSY)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.availability.get_calendar(
                "cal_abc123",
                start="2026-03-28T09:00:00Z",
                end="2026-03-28T17:00:00Z",
                include_busy=True,
            )
            assert result.busy is not None
            assert len(result.busy) == 1

    @respx.mock
    def test_find_meeting_time(self) -> None:
        respx.get(f"{BASE}/v1/availability").mock(
            return_value=httpx.Response(200, json=CROSS_AVAIL_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.availability.find_meeting_time(
                agents=["agt_1", "agt_2"],
                start="2026-03-28T09:00:00Z",
                end="2026-03-28T17:00:00Z",
                slot_duration="30m",
            )
            assert isinstance(result, AgentAvailabilityResponse)
            assert result.agents == ["agt_1", "agt_2"]
            assert len(result.slots) == 1

    @respx.mock
    def test_duration_param_forwarded(self) -> None:
        """Passing duration sends duration and not slot_duration."""
        route = respx.get(f"{BASE}/v1/agents/agt_abc123/availability").mock(
            return_value=httpx.Response(200, json=AGENT_AVAIL_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            client.availability.get(
                "agt_abc123",
                start="2026-03-28T09:00:00Z",
                end="2026-03-28T17:00:00Z",
                duration="45m",
            )
        request = route.calls.last.request
        assert request.url.params.get("duration") == "45m"
        assert "slot_duration" not in request.url.params

    @respx.mock
    def test_slot_duration_still_works(self) -> None:
        """The deprecated slot_duration alias still forwards, without duration."""
        route = respx.get(f"{BASE}/v1/agents/agt_abc123/availability").mock(
            return_value=httpx.Response(200, json=AGENT_AVAIL_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            client.availability.get(
                "agt_abc123",
                start="2026-03-28T09:00:00Z",
                end="2026-03-28T17:00:00Z",
                slot_duration="1h",
            )
        request = route.calls.last.request
        assert request.url.params.get("slot_duration") == "1h"
        assert "duration" not in request.url.params

    @respx.mock
    def test_find_meeting_time_duration_forwarded(self) -> None:
        route = respx.get(f"{BASE}/v1/availability").mock(
            return_value=httpx.Response(200, json=CROSS_AVAIL_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            client.availability.find_meeting_time(
                agents=["agt_1", "agt_2"],
                start="2026-03-28T09:00:00Z",
                end="2026-03-28T17:00:00Z",
                duration="30m",
            )
        request = route.calls.last.request
        assert request.url.params.get("duration") == "30m"
        assert "slot_duration" not in request.url.params

    @respx.mock
    def test_request_id(self) -> None:
        respx.get(f"{BASE}/v1/agents/agt_abc123/availability").mock(
            return_value=httpx.Response(
                200, json=AGENT_AVAIL_DATA, headers={"X-Request-Id": "req_avail_1"}
            )
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.availability.get(
                "agt_abc123",
                start="2026-03-28T09:00:00Z",
                end="2026-03-28T17:00:00Z",
            )
            assert result._request_id == "req_avail_1"

    @respx.mock
    def test_agent_scoped_availability(self) -> None:
        """client.agents.availability.get() reaches the same endpoint."""
        respx.get(f"{BASE}/v1/agents/agt_abc123/availability").mock(
            return_value=httpx.Response(200, json=AGENT_AVAIL_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.agents.availability.get(
                "agt_abc123",
                start="2026-03-28T09:00:00Z",
                end="2026-03-28T17:00:00Z",
            )
            assert isinstance(result, AgentAvailabilityResponse)
            assert len(result.slots) == 2


# ---------------------------------------------------------------------------
# Async tests
# ---------------------------------------------------------------------------


class TestAsyncAvailability:
    @respx.mock
    async def test_get_agent(self) -> None:
        respx.get(f"{BASE}/v1/agents/agt_abc123/availability").mock(
            return_value=httpx.Response(200, json=AGENT_AVAIL_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = await client.availability.get(
                "agt_abc123",
                start="2026-03-28T09:00:00Z",
                end="2026-03-28T17:00:00Z",
            )
            assert isinstance(result, AgentAvailabilityResponse)
            assert len(result.slots) == 2

    @respx.mock
    async def test_get_calendar(self) -> None:
        respx.get(f"{BASE}/v1/calendars/cal_abc123/availability").mock(
            return_value=httpx.Response(200, json=CALENDAR_AVAIL_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = await client.availability.get_calendar(
                "cal_abc123",
                start="2026-03-28T09:00:00Z",
                end="2026-03-28T17:00:00Z",
            )
            assert isinstance(result, CalendarAvailabilityResponse)
            assert result.calendar_id == "cal_abc123"

    @respx.mock
    async def test_find_meeting_time(self) -> None:
        respx.get(f"{BASE}/v1/availability").mock(
            return_value=httpx.Response(200, json=CROSS_AVAIL_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = await client.availability.find_meeting_time(
                agents=["agt_1", "agt_2"],
                start="2026-03-28T09:00:00Z",
                end="2026-03-28T17:00:00Z",
            )
            assert isinstance(result, AgentAvailabilityResponse)
            assert len(result.slots) == 1

    @respx.mock
    async def test_duration_param_forwarded(self) -> None:
        """Passing duration sends duration and not slot_duration."""
        route = respx.get(f"{BASE}/v1/calendars/cal_abc123/availability").mock(
            return_value=httpx.Response(200, json=CALENDAR_AVAIL_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            await client.availability.get_calendar(
                "cal_abc123",
                start="2026-03-28T09:00:00Z",
                end="2026-03-28T17:00:00Z",
                duration="45m",
            )
        request = route.calls.last.request
        assert request.url.params.get("duration") == "45m"
        assert "slot_duration" not in request.url.params

    @respx.mock
    async def test_slot_duration_still_works(self) -> None:
        """The deprecated slot_duration alias still forwards, without duration."""
        route = respx.get(f"{BASE}/v1/calendars/cal_abc123/availability").mock(
            return_value=httpx.Response(200, json=CALENDAR_AVAIL_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            await client.availability.get_calendar(
                "cal_abc123",
                start="2026-03-28T09:00:00Z",
                end="2026-03-28T17:00:00Z",
                slot_duration="1h",
            )
        request = route.calls.last.request
        assert request.url.params.get("slot_duration") == "1h"
        assert "duration" not in request.url.params
