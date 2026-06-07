from __future__ import annotations

from datetime import datetime  # noqa: TCH003 — Pydantic needs this at runtime
from typing import Any, Literal

from pydantic import Field
from typing_extensions import NotRequired, Required, TypedDict

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource
from ..pagination import AsyncPager, ListResponse, SyncPager
from .events import Event

AgentStatus = Literal["idle", "working", "waiting", "error"]

# Sentinel for distinguishing "not passed" from "explicitly passed None"
_UNSET: Any = object()

# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------


class Calendar(ChronaryModel):
    """A calendar registered with the Chronary API."""

    id: str
    name: str
    timezone: str
    agent_id: str | None = Field(default=None, alias="agentId")
    metadata: dict[str, Any]
    ical_url: str | None = None  # API returns snake_case for this field
    external_id: str | None = Field(default=None, alias="externalId")
    provider: str | None = None
    # Default reminder offsets (minutes before start) applied to events that don't set
    # their own. Each entry is between 1 and 40320 (28 days); max 5 entries. The system
    # default is [10] (10 minutes).
    default_reminders: list[int] | None = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


# ---------------------------------------------------------------------------
# Request param TypedDicts
# ---------------------------------------------------------------------------


class CalendarCreateParams(TypedDict):
    name: Required[str]
    timezone: Required[str]
    agent_status: NotRequired[AgentStatus]
    metadata: NotRequired[dict[str, Any]]
    # Default reminder offsets (minutes before start) for events on this calendar.
    # Max 5 entries, each between 1 and 40320 (28 days). The system default is [10].
    default_reminders: NotRequired[list[int]]


class CalendarUpdateParams(TypedDict, total=False):
    name: str
    timezone: str
    agent_status: AgentStatus
    metadata: dict[str, Any]
    default_reminders: list[int]


class CalendarListParams(TypedDict, total=False):
    include: Literal["all"]
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Calendar context
# ---------------------------------------------------------------------------


class CalendarContext(ChronaryModel):
    """Temporal snapshot of a calendar: now, current event, recent, upcoming."""

    calendar_id: str
    now: datetime
    agent_status: AgentStatus
    current_event: Event | None = None
    next_event: Event | None = None
    recent_events: list[Event] = Field(default_factory=list)
    upcoming: list[Event] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Availability rules
# ---------------------------------------------------------------------------


class WorkingHoursDay(TypedDict):
    start: Required[str]
    end: Required[str]


class WorkingHoursParams(TypedDict, total=False):
    mon: WorkingHoursDay
    tue: WorkingHoursDay
    wed: WorkingHoursDay
    thu: WorkingHoursDay
    fri: WorkingHoursDay
    sat: WorkingHoursDay
    sun: WorkingHoursDay


class AvailabilityRules(ChronaryModel):
    """Buffer and working-hours rules for a calendar."""

    id: str
    calendar_id: str
    buffer_before_minutes: int
    buffer_after_minutes: int
    working_hours: dict[str, Any] | None = None
    timezone: str
    created_at: datetime
    updated_at: datetime


class SetAvailabilityRulesParams(TypedDict, total=False):
    buffer_before_minutes: int
    buffer_after_minutes: int
    working_hours: WorkingHoursParams | None
    timezone: str


# ---------------------------------------------------------------------------
# Sync resource — org-scoped
# ---------------------------------------------------------------------------

_CALENDARS_PATH = "/v1/calendars"


class Calendars(SyncAPIResource):
    """client.calendars — synchronous CRUD for calendar resources."""

    def create(
        self,
        *,
        name: str,
        timezone: str,
        agent_status: AgentStatus | None = None,
        metadata: dict[str, Any] | None = None,
        default_reminders: list[int] | None = None,
        max_retries: int | None = None,
    ) -> Calendar:
        body: dict[str, Any] = {"name": name, "timezone": timezone}
        if agent_status is not None:
            body["agent_status"] = agent_status
        if metadata is not None:
            body["metadata"] = metadata
        if default_reminders is not None:
            body["default_reminders"] = default_reminders
        resp = self._request("POST", _CALENDARS_PATH, json=body, max_retries=max_retries)
        return self._build(Calendar, resp)

    def list(
        self,
        *,
        include: Literal["all"] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> SyncPager[Calendar]:
        params: dict[str, Any] = {
            "include": include,
            "limit": limit,
            "offset": offset,
        }
        resp = self._request("GET", _CALENDARS_PATH, params=params, max_retries=max_retries)
        raw = resp.json()
        list_resp = ListResponse[Calendar](
            data=[Calendar.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return SyncPager(
            list_resp,
            client=self._client,
            path=_CALENDARS_PATH,
            params=params,
            model=Calendar,
            request_id=resp.headers.get("X-Request-Id"),
        )

    def get(
        self,
        calendar_id: str,
        *,
        max_retries: int | None = None,
    ) -> Calendar:
        resp = self._request("GET", f"{_CALENDARS_PATH}/{calendar_id}", max_retries=max_retries)
        return self._build(Calendar, resp)

    def update(
        self,
        calendar_id: str,
        *,
        name: str | None = None,
        timezone: str | None = None,
        agent_status: AgentStatus | None = None,
        metadata: dict[str, Any] | None = None,
        default_reminders: list[int] | None = _UNSET,  # type: ignore[assignment]
        max_retries: int | None = None,
    ) -> Calendar:
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if timezone is not None:
            body["timezone"] = timezone
        if agent_status is not None:
            body["agent_status"] = agent_status
        if metadata is not None:
            body["metadata"] = metadata
        if default_reminders is not _UNSET:
            body["default_reminders"] = default_reminders
        resp = self._request(
            "PATCH", f"{_CALENDARS_PATH}/{calendar_id}", json=body, max_retries=max_retries
        )
        return self._build(Calendar, resp)

    def delete(
        self,
        calendar_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        self._request("DELETE", f"{_CALENDARS_PATH}/{calendar_id}", max_retries=max_retries)

    def get_context(
        self,
        calendar_id: str,
        *,
        max_retries: int | None = None,
    ) -> CalendarContext:
        path = f"{_CALENDARS_PATH}/{calendar_id}/context"
        resp = self._request("GET", path, max_retries=max_retries)
        return self._build(CalendarContext, resp)

    def set_availability_rules(
        self,
        calendar_id: str,
        *,
        buffer_before_minutes: int | None = None,
        buffer_after_minutes: int | None = None,
        working_hours: WorkingHoursParams | None = None,
        timezone: str | None = None,
        max_retries: int | None = None,
    ) -> AvailabilityRules:
        body: dict[str, Any] = {}
        if buffer_before_minutes is not None:
            body["buffer_before_minutes"] = buffer_before_minutes
        if buffer_after_minutes is not None:
            body["buffer_after_minutes"] = buffer_after_minutes
        if working_hours is not None:
            body["working_hours"] = working_hours
        if timezone is not None:
            body["timezone"] = timezone
        path = f"{_CALENDARS_PATH}/{calendar_id}/availability-rules"
        resp = self._request("PUT", path, json=body, max_retries=max_retries)
        return self._build(AvailabilityRules, resp)

    def get_availability_rules(
        self,
        calendar_id: str,
        *,
        max_retries: int | None = None,
    ) -> AvailabilityRules:
        path = f"{_CALENDARS_PATH}/{calendar_id}/availability-rules"
        resp = self._request("GET", path, max_retries=max_retries)
        return self._build(AvailabilityRules, resp)

    def delete_availability_rules(
        self,
        calendar_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        path = f"{_CALENDARS_PATH}/{calendar_id}/availability-rules"
        self._request("DELETE", path, max_retries=max_retries)


# ---------------------------------------------------------------------------
# Async resource — org-scoped
# ---------------------------------------------------------------------------


class AsyncCalendars(AsyncAPIResource):
    """client.calendars — asynchronous CRUD for calendar resources."""

    async def create(
        self,
        *,
        name: str,
        timezone: str,
        agent_status: AgentStatus | None = None,
        metadata: dict[str, Any] | None = None,
        default_reminders: list[int] | None = None,
        max_retries: int | None = None,
    ) -> Calendar:
        body: dict[str, Any] = {"name": name, "timezone": timezone}
        if agent_status is not None:
            body["agent_status"] = agent_status
        if metadata is not None:
            body["metadata"] = metadata
        if default_reminders is not None:
            body["default_reminders"] = default_reminders
        resp = await self._request("POST", _CALENDARS_PATH, json=body, max_retries=max_retries)
        return self._build(Calendar, resp)

    async def list(
        self,
        *,
        include: Literal["all"] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> AsyncPager[Calendar]:
        params: dict[str, Any] = {
            "include": include,
            "limit": limit,
            "offset": offset,
        }
        resp = await self._request(
            "GET", _CALENDARS_PATH, params=params, max_retries=max_retries
        )
        raw = resp.json()
        list_resp = ListResponse[Calendar](
            data=[Calendar.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return AsyncPager(
            list_resp,
            client=self._client,
            path=_CALENDARS_PATH,
            params=params,
            model=Calendar,
            request_id=resp.headers.get("X-Request-Id"),
        )

    async def get(
        self,
        calendar_id: str,
        *,
        max_retries: int | None = None,
    ) -> Calendar:
        resp = await self._request(
            "GET", f"{_CALENDARS_PATH}/{calendar_id}", max_retries=max_retries
        )
        return self._build(Calendar, resp)

    async def update(
        self,
        calendar_id: str,
        *,
        name: str | None = None,
        timezone: str | None = None,
        agent_status: AgentStatus | None = None,
        metadata: dict[str, Any] | None = None,
        default_reminders: list[int] | None = _UNSET,  # type: ignore[assignment]
        max_retries: int | None = None,
    ) -> Calendar:
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if timezone is not None:
            body["timezone"] = timezone
        if agent_status is not None:
            body["agent_status"] = agent_status
        if metadata is not None:
            body["metadata"] = metadata
        if default_reminders is not _UNSET:
            body["default_reminders"] = default_reminders
        resp = await self._request(
            "PATCH", f"{_CALENDARS_PATH}/{calendar_id}", json=body, max_retries=max_retries
        )
        return self._build(Calendar, resp)

    async def delete(
        self,
        calendar_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        await self._request(
            "DELETE", f"{_CALENDARS_PATH}/{calendar_id}", max_retries=max_retries
        )

    async def get_context(
        self,
        calendar_id: str,
        *,
        max_retries: int | None = None,
    ) -> CalendarContext:
        path = f"{_CALENDARS_PATH}/{calendar_id}/context"
        resp = await self._request("GET", path, max_retries=max_retries)
        return self._build(CalendarContext, resp)

    async def set_availability_rules(
        self,
        calendar_id: str,
        *,
        buffer_before_minutes: int | None = None,
        buffer_after_minutes: int | None = None,
        working_hours: WorkingHoursParams | None = None,
        timezone: str | None = None,
        max_retries: int | None = None,
    ) -> AvailabilityRules:
        body: dict[str, Any] = {}
        if buffer_before_minutes is not None:
            body["buffer_before_minutes"] = buffer_before_minutes
        if buffer_after_minutes is not None:
            body["buffer_after_minutes"] = buffer_after_minutes
        if working_hours is not None:
            body["working_hours"] = working_hours
        if timezone is not None:
            body["timezone"] = timezone
        path = f"{_CALENDARS_PATH}/{calendar_id}/availability-rules"
        resp = await self._request("PUT", path, json=body, max_retries=max_retries)
        return self._build(AvailabilityRules, resp)

    async def get_availability_rules(
        self,
        calendar_id: str,
        *,
        max_retries: int | None = None,
    ) -> AvailabilityRules:
        path = f"{_CALENDARS_PATH}/{calendar_id}/availability-rules"
        resp = await self._request("GET", path, max_retries=max_retries)
        return self._build(AvailabilityRules, resp)

    async def delete_availability_rules(
        self,
        calendar_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        path = f"{_CALENDARS_PATH}/{calendar_id}/availability-rules"
        await self._request("DELETE", path, max_retries=max_retries)


# ---------------------------------------------------------------------------
# Sync agent-scoped sub-resource
# ---------------------------------------------------------------------------

_AGENT_CALENDARS_PATH = "/v1/agents/{agent_id}/calendars"


class AgentCalendars(SyncAPIResource):
    """client.agents.calendars — agent-scoped calendar operations."""

    def create(
        self,
        agent_id: str,
        *,
        name: str,
        timezone: str,
        agent_status: AgentStatus | None = None,
        metadata: dict[str, Any] | None = None,
        default_reminders: list[int] | None = None,
        max_retries: int | None = None,
    ) -> Calendar:
        path = _AGENT_CALENDARS_PATH.format(agent_id=agent_id)
        body: dict[str, Any] = {"name": name, "timezone": timezone}
        if agent_status is not None:
            body["agent_status"] = agent_status
        if metadata is not None:
            body["metadata"] = metadata
        if default_reminders is not None:
            body["default_reminders"] = default_reminders
        resp = self._request("POST", path, json=body, max_retries=max_retries)
        return self._build(Calendar, resp)

    def list(
        self,
        agent_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> SyncPager[Calendar]:
        path = _AGENT_CALENDARS_PATH.format(agent_id=agent_id)
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        resp = self._request("GET", path, params=params, max_retries=max_retries)
        raw = resp.json()
        list_resp = ListResponse[Calendar](
            data=[Calendar.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return SyncPager(
            list_resp,
            client=self._client,
            path=path,
            params=params,
            model=Calendar,
            request_id=resp.headers.get("X-Request-Id"),
        )


# ---------------------------------------------------------------------------
# Async agent-scoped sub-resource
# ---------------------------------------------------------------------------


class AsyncAgentCalendars(AsyncAPIResource):
    """client.agents.calendars — async agent-scoped calendar operations."""

    async def create(
        self,
        agent_id: str,
        *,
        name: str,
        timezone: str,
        agent_status: AgentStatus | None = None,
        metadata: dict[str, Any] | None = None,
        default_reminders: list[int] | None = None,
        max_retries: int | None = None,
    ) -> Calendar:
        path = _AGENT_CALENDARS_PATH.format(agent_id=agent_id)
        body: dict[str, Any] = {"name": name, "timezone": timezone}
        if agent_status is not None:
            body["agent_status"] = agent_status
        if metadata is not None:
            body["metadata"] = metadata
        if default_reminders is not None:
            body["default_reminders"] = default_reminders
        resp = await self._request("POST", path, json=body, max_retries=max_retries)
        return self._build(Calendar, resp)

    async def list(
        self,
        agent_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> AsyncPager[Calendar]:
        path = _AGENT_CALENDARS_PATH.format(agent_id=agent_id)
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        resp = await self._request("GET", path, params=params, max_retries=max_retries)
        raw = resp.json()
        list_resp = ListResponse[Calendar](
            data=[Calendar.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return AsyncPager(
            list_resp,
            client=self._client,
            path=path,
            params=params,
            model=Calendar,
            request_id=resp.headers.get("X-Request-Id"),
        )
