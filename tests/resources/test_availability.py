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

AGENT_AVAIL_DATA = {
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
        respx.get(f"{BASE}/v1/agents/agt_abc123/availability").mock(
            return_value=httpx.Response(200, json=AGENT_AVAIL_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.availability.get(
                "agt_abc123",
                start="2026-03-28T09:00:00Z",
                end="2026-03-28T17:00:00Z",
            )
            assert isinstance(result, AgentAvailabilityResponse)
            assert result.agents == ["agt_abc123"]
            assert len(result.slots) == 2
            assert isinstance(result.slots[0], TimeSlot)
            assert result.per_agent_busy is None

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
