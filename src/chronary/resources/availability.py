from __future__ import annotations

from typing import Any, Literal

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class TimeSlot(ChronaryModel):
    """A free time slot."""

    start: str
    end: str


class BusyBlock(ChronaryModel):
    """A busy block with optional calendar_id."""

    start: str
    end: str
    calendar_id: str | None = None


class AgentAvailabilityResponse(ChronaryModel):
    """Availability response for one or more agents."""

    agents: list[str]
    slots: list[TimeSlot]
    per_agent_busy: dict[str, list[BusyBlock]] | None = None


class CalendarAvailabilityResponse(ChronaryModel):
    """Availability response for a single calendar."""

    calendar_id: str
    slots: list[TimeSlot]
    busy: list[BusyBlock] | None = None


# ---------------------------------------------------------------------------
# Sync resource
# ---------------------------------------------------------------------------

_AGENT_AVAIL_PATH = "/v1/agents/{agent_id}/availability"
_CAL_AVAIL_PATH = "/v1/calendars/{calendar_id}/availability"
_CROSS_AVAIL_PATH = "/v1/availability"


class Availability(SyncAPIResource):
    """client.availability — synchronous availability queries."""

    def get(
        self,
        agent_id: str,
        *,
        start: str,
        end: str,
        duration: Literal["15m", "30m", "45m", "1h", "2h"] | None = None,
        slot_duration: Literal["15m", "30m", "45m", "1h", "2h"] | None = None,
        include_busy: bool | None = None,
        max_retries: int | None = None,
    ) -> AgentAvailabilityResponse:
        """Get availability slots for an agent.

        Args:
            agent_id: The agent to query.
            start: ISO 8601 start of the window.
            end: ISO 8601 end of the window.
            duration: Desired slot length. Preferred parameter.
            slot_duration: DEPRECATED alias for ``duration``. Prefer ``duration``.
                Only pass one; sending both with different values is a 400.
            include_busy: Include busy blocks in the response.
        """
        path = _AGENT_AVAIL_PATH.format(agent_id=agent_id)
        params: dict[str, Any] = {
            "start": start,
            "end": end,
            "duration": duration,
            "slot_duration": slot_duration,
            "include_busy": "true" if include_busy else None,
        }
        resp = self._request("GET", path, params=params, max_retries=max_retries)
        return self._build(AgentAvailabilityResponse, resp)

    def get_calendar(
        self,
        calendar_id: str,
        *,
        start: str,
        end: str,
        duration: Literal["15m", "30m", "45m", "1h", "2h"] | None = None,
        slot_duration: Literal["15m", "30m", "45m", "1h", "2h"] | None = None,
        include_busy: bool | None = None,
        max_retries: int | None = None,
    ) -> CalendarAvailabilityResponse:
        """Get availability slots for a calendar.

        Args:
            calendar_id: The calendar to query.
            start: ISO 8601 start of the window.
            end: ISO 8601 end of the window.
            duration: Desired slot length. Preferred parameter.
            slot_duration: DEPRECATED alias for ``duration``. Prefer ``duration``.
                Only pass one; sending both with different values is a 400.
            include_busy: Include busy blocks in the response.
        """
        path = _CAL_AVAIL_PATH.format(calendar_id=calendar_id)
        params: dict[str, Any] = {
            "start": start,
            "end": end,
            "duration": duration,
            "slot_duration": slot_duration,
            "include_busy": "true" if include_busy else None,
        }
        resp = self._request("GET", path, params=params, max_retries=max_retries)
        return self._build(CalendarAvailabilityResponse, resp)

    def find_meeting_time(
        self,
        *,
        agents: list[str],
        start: str,
        end: str,
        duration: Literal["15m", "30m", "45m", "1h", "2h"] | None = None,
        slot_duration: Literal["15m", "30m", "45m", "1h", "2h"] | None = None,
        calendars: list[str] | None = None,
        include_busy: bool | None = None,
        max_retries: int | None = None,
    ) -> AgentAvailabilityResponse:
        """Find a common meeting time across agents.

        Args:
            agents: Agents to intersect availability for.
            start: ISO 8601 start of the window.
            end: ISO 8601 end of the window.
            duration: Desired slot length. Preferred parameter.
            slot_duration: DEPRECATED alias for ``duration``. Prefer ``duration``.
                Only pass one; sending both with different values is a 400.
            calendars: Optional calendars to include.
            include_busy: Include busy blocks in the response.
        """
        params: dict[str, Any] = {
            "agents": ",".join(agents),
            "start": start,
            "end": end,
            "duration": duration,
            "slot_duration": slot_duration,
            "calendars": ",".join(calendars) if calendars else None,
            "include_busy": "true" if include_busy else None,
        }
        resp = self._request(
            "GET", _CROSS_AVAIL_PATH, params=params, max_retries=max_retries
        )
        return self._build(AgentAvailabilityResponse, resp)


# ---------------------------------------------------------------------------
# Async resource
# ---------------------------------------------------------------------------


class AsyncAvailability(AsyncAPIResource):
    """client.availability — asynchronous availability queries."""

    async def get(
        self,
        agent_id: str,
        *,
        start: str,
        end: str,
        duration: Literal["15m", "30m", "45m", "1h", "2h"] | None = None,
        slot_duration: Literal["15m", "30m", "45m", "1h", "2h"] | None = None,
        include_busy: bool | None = None,
        max_retries: int | None = None,
    ) -> AgentAvailabilityResponse:
        """Get availability slots for an agent.

        Args:
            agent_id: The agent to query.
            start: ISO 8601 start of the window.
            end: ISO 8601 end of the window.
            duration: Desired slot length. Preferred parameter.
            slot_duration: DEPRECATED alias for ``duration``. Prefer ``duration``.
                Only pass one; sending both with different values is a 400.
            include_busy: Include busy blocks in the response.
        """
        path = _AGENT_AVAIL_PATH.format(agent_id=agent_id)
        params: dict[str, Any] = {
            "start": start,
            "end": end,
            "duration": duration,
            "slot_duration": slot_duration,
            "include_busy": "true" if include_busy else None,
        }
        resp = await self._request("GET", path, params=params, max_retries=max_retries)
        return self._build(AgentAvailabilityResponse, resp)

    async def get_calendar(
        self,
        calendar_id: str,
        *,
        start: str,
        end: str,
        duration: Literal["15m", "30m", "45m", "1h", "2h"] | None = None,
        slot_duration: Literal["15m", "30m", "45m", "1h", "2h"] | None = None,
        include_busy: bool | None = None,
        max_retries: int | None = None,
    ) -> CalendarAvailabilityResponse:
        """Get availability slots for a calendar.

        Args:
            calendar_id: The calendar to query.
            start: ISO 8601 start of the window.
            end: ISO 8601 end of the window.
            duration: Desired slot length. Preferred parameter.
            slot_duration: DEPRECATED alias for ``duration``. Prefer ``duration``.
                Only pass one; sending both with different values is a 400.
            include_busy: Include busy blocks in the response.
        """
        path = _CAL_AVAIL_PATH.format(calendar_id=calendar_id)
        params: dict[str, Any] = {
            "start": start,
            "end": end,
            "duration": duration,
            "slot_duration": slot_duration,
            "include_busy": "true" if include_busy else None,
        }
        resp = await self._request("GET", path, params=params, max_retries=max_retries)
        return self._build(CalendarAvailabilityResponse, resp)

    async def find_meeting_time(
        self,
        *,
        agents: list[str],
        start: str,
        end: str,
        duration: Literal["15m", "30m", "45m", "1h", "2h"] | None = None,
        slot_duration: Literal["15m", "30m", "45m", "1h", "2h"] | None = None,
        calendars: list[str] | None = None,
        include_busy: bool | None = None,
        max_retries: int | None = None,
    ) -> AgentAvailabilityResponse:
        """Find a common meeting time across agents.

        Args:
            agents: Agents to intersect availability for.
            start: ISO 8601 start of the window.
            end: ISO 8601 end of the window.
            duration: Desired slot length. Preferred parameter.
            slot_duration: DEPRECATED alias for ``duration``. Prefer ``duration``.
                Only pass one; sending both with different values is a 400.
            calendars: Optional calendars to include.
            include_busy: Include busy blocks in the response.
        """
        params: dict[str, Any] = {
            "agents": ",".join(agents),
            "start": start,
            "end": end,
            "duration": duration,
            "slot_duration": slot_duration,
            "calendars": ",".join(calendars) if calendars else None,
            "include_busy": "true" if include_busy else None,
        }
        resp = await self._request(
            "GET", _CROSS_AVAIL_PATH, params=params, max_retries=max_retries
        )
        return self._build(AgentAvailabilityResponse, resp)
