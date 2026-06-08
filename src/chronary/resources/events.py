from __future__ import annotations

from datetime import datetime  # noqa: TCH003 — Pydantic needs this at runtime
from typing import Any, Literal

from pydantic import Field
from typing_extensions import NotRequired, Required, TypedDict

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource
from ..pagination import AsyncPager, ListResponse, SyncPager

# Sentinel for distinguishing "not passed" from "explicitly passed None"
_UNSET: Any = object()


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------


EventStatus = Literal["confirmed", "tentative", "cancelled", "hold"]


class Event(ChronaryModel):
    """A calendar event."""

    id: str
    calendar_id: str = Field(alias="calendarId")
    title: str
    description: str | None = None
    start_time: datetime = Field(alias="startTime")
    end_time: datetime = Field(alias="endTime")
    all_day: bool = Field(default=False, alias="allDay")
    status: EventStatus
    source: Literal["internal", "external_ical"] = "internal"
    metadata: dict[str, Any] = Field(default_factory=dict)
    hold_expires_at: datetime | None = Field(default=None, alias="holdExpiresAt")
    hold_priority: int | None = Field(default=None, alias="holdPriority")
    # Reminder offsets in minutes before start_time (e.g. [10, 1440]); max 5 entries,
    # each between 1 and 40320 (28 days). None means "inherit the calendar default";
    # [] means "no reminders". The system default is [10] (10 minutes). Each reminder
    # fires an event.reminder webhook and shows as a VALARM in the iCal feed.
    reminders: list[int] | None = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


# ---------------------------------------------------------------------------
# Request param TypedDicts
# ---------------------------------------------------------------------------


class EventCreateParams(TypedDict):
    title: Required[str]
    start_time: Required[str]
    end_time: Required[str]
    description: NotRequired[str]
    all_day: NotRequired[bool]
    status: NotRequired[EventStatus]
    metadata: NotRequired[dict[str, Any]]
    # Reminder offsets in minutes before start_time (e.g. [10, 1440]); max 5 entries,
    # each between 1 and 40320 (28 days). Omit to inherit the calendar default ([10]);
    # pass [] for no reminders.
    reminders: NotRequired[list[int]]
    # Hold-specific fields (required/valid only when status='hold').
    hold_expires_at: NotRequired[str]
    hold_priority: NotRequired[int]


class EventUpdateParams(TypedDict, total=False):
    title: str
    description: str | None
    start_time: str
    end_time: str
    all_day: bool
    # Holds cannot be updated via PATCH — use confirm() or release() instead.
    status: Literal["confirmed", "tentative", "cancelled"]
    metadata: dict[str, Any]
    # Reminder offsets in minutes before start_time (e.g. [10, 1440]); max 5 entries,
    # each between 1 and 40320 (28 days). [] clears reminders.
    reminders: list[int]


class EventListParams(TypedDict, total=False):
    start_after: str
    start_before: str
    status: EventStatus
    source: Literal["internal", "external_ical"]
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Sync resource
# ---------------------------------------------------------------------------

_EVENTS_PATH = "/v1/calendars/{calendar_id}/events"
_EVENT_BY_ID_PATH = "/v1/events/{event_id}"
_EVENTS_CONFIRM_PATH = "/v1/events/{event_id}/confirm"
_EVENTS_RELEASE_PATH = "/v1/events/{event_id}/release"


class Events(SyncAPIResource):
    """client.events — synchronous CRUD for calendar events."""

    def create(
        self,
        calendar_id: str,
        *,
        title: str,
        start_time: str,
        end_time: str,
        description: str | None = None,
        all_day: bool | None = None,
        status: EventStatus | None = None,
        metadata: dict[str, Any] | None = None,
        reminders: list[int] | None = None,
        hold_expires_at: str | None = None,
        hold_priority: int | None = None,
        max_retries: int | None = None,
    ) -> Event:
        path = _EVENTS_PATH.format(calendar_id=calendar_id)
        body: dict[str, Any] = {
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
        }
        if description is not None:
            body["description"] = description
        if all_day is not None:
            body["all_day"] = all_day
        if status is not None:
            body["status"] = status
        if metadata is not None:
            body["metadata"] = metadata
        if reminders is not None:
            body["reminders"] = reminders
        if hold_expires_at is not None:
            body["hold_expires_at"] = hold_expires_at
        if hold_priority is not None:
            body["hold_priority"] = hold_priority
        resp = self._request("POST", path, json=body, max_retries=max_retries)
        return self._build(Event, resp)

    def list(
        self,
        calendar_id: str,
        *,
        start_after: str | None = None,
        start_before: str | None = None,
        status: EventStatus | None = None,
        source: Literal["internal", "external_ical"] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> SyncPager[Event]:
        path = _EVENTS_PATH.format(calendar_id=calendar_id)
        params: dict[str, Any] = {
            "start_after": start_after,
            "start_before": start_before,
            "status": status,
            "source": source,
            "limit": limit,
            "offset": offset,
        }
        resp = self._request("GET", path, params=params, max_retries=max_retries)
        raw = resp.json()
        list_resp = ListResponse[Event](
            data=[Event.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return SyncPager(
            list_resp,
            client=self._client,
            path=path,
            params=params,
            model=Event,
            request_id=resp.headers.get("X-Request-Id"),
        )

    def get(
        self,
        calendar_id: str,
        event_id: str,
        *,
        max_retries: int | None = None,
    ) -> Event:
        path = f"{_EVENTS_PATH.format(calendar_id=calendar_id)}/{event_id}"
        resp = self._request("GET", path, max_retries=max_retries)
        return self._build(Event, resp)

    def update(
        self,
        calendar_id: str,
        event_id: str,
        *,
        title: str | None = None,
        description: str | None = _UNSET,  # type: ignore[assignment]
        start_time: str | None = None,
        end_time: str | None = None,
        all_day: bool | None = None,
        status: Literal["confirmed", "tentative", "cancelled"] | None = None,
        metadata: dict[str, Any] | None = None,
        reminders: list[int] | None = _UNSET,  # type: ignore[assignment]
        max_retries: int | None = None,
    ) -> Event:
        path = f"{_EVENTS_PATH.format(calendar_id=calendar_id)}/{event_id}"
        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = title
        if description is not _UNSET:
            body["description"] = description
        if start_time is not None:
            body["start_time"] = start_time
        if end_time is not None:
            body["end_time"] = end_time
        if all_day is not None:
            body["all_day"] = all_day
        if status is not None:
            body["status"] = status
        if metadata is not None:
            body["metadata"] = metadata
        if reminders is not _UNSET:
            body["reminders"] = reminders
        resp = self._request("PATCH", path, json=body, max_retries=max_retries)
        return self._build(Event, resp)

    def delete(
        self,
        calendar_id: str,
        event_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        path = f"{_EVENTS_PATH.format(calendar_id=calendar_id)}/{event_id}"
        self._request("DELETE", path, max_retries=max_retries)

    def get_by_id(
        self,
        event_id: str,
        *,
        max_retries: int | None = None,
    ) -> Event:
        """Fetch an event by ID alone — the calendar is resolved internally."""
        path = _EVENT_BY_ID_PATH.format(event_id=event_id)
        resp = self._request("GET", path, max_retries=max_retries)
        return self._build(Event, resp)

    def update_by_id(
        self,
        event_id: str,
        *,
        title: str | None = None,
        description: str | None = _UNSET,  # type: ignore[assignment]
        start_time: str | None = None,
        end_time: str | None = None,
        all_day: bool | None = None,
        status: Literal["confirmed", "tentative", "cancelled"] | None = None,
        metadata: dict[str, Any] | None = None,
        reminders: list[int] | None = _UNSET,  # type: ignore[assignment]
        max_retries: int | None = None,
    ) -> Event:
        """Update an event by ID alone — the calendar is resolved internally."""
        path = _EVENT_BY_ID_PATH.format(event_id=event_id)
        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = title
        if description is not _UNSET:
            body["description"] = description
        if start_time is not None:
            body["start_time"] = start_time
        if end_time is not None:
            body["end_time"] = end_time
        if all_day is not None:
            body["all_day"] = all_day
        if status is not None:
            body["status"] = status
        if metadata is not None:
            body["metadata"] = metadata
        if reminders is not _UNSET:
            body["reminders"] = reminders
        resp = self._request("PATCH", path, json=body, max_retries=max_retries)
        return self._build(Event, resp)

    def delete_by_id(
        self,
        event_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        """Delete an event by ID alone — the calendar is resolved internally."""
        path = _EVENT_BY_ID_PATH.format(event_id=event_id)
        self._request("DELETE", path, max_retries=max_retries)

    def confirm(
        self,
        event_id: str,
        *,
        max_retries: int | None = None,
    ) -> Event:
        """Promote a held event (status='hold') to status='confirmed'."""
        path = _EVENTS_CONFIRM_PATH.format(event_id=event_id)
        resp = self._request("PUT", path, max_retries=max_retries)
        return self._build(Event, resp)

    def release(
        self,
        event_id: str,
        *,
        max_retries: int | None = None,
    ) -> Event:
        """Manually release a held event before its TTL, freeing the slot."""
        path = _EVENTS_RELEASE_PATH.format(event_id=event_id)
        resp = self._request("PUT", path, max_retries=max_retries)
        return self._build(Event, resp)


# ---------------------------------------------------------------------------
# Async resource
# ---------------------------------------------------------------------------


class AsyncEvents(AsyncAPIResource):
    """client.events — asynchronous CRUD for calendar events."""

    async def create(
        self,
        calendar_id: str,
        *,
        title: str,
        start_time: str,
        end_time: str,
        description: str | None = None,
        all_day: bool | None = None,
        status: EventStatus | None = None,
        metadata: dict[str, Any] | None = None,
        reminders: list[int] | None = None,
        hold_expires_at: str | None = None,
        hold_priority: int | None = None,
        max_retries: int | None = None,
    ) -> Event:
        path = _EVENTS_PATH.format(calendar_id=calendar_id)
        body: dict[str, Any] = {
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
        }
        if description is not None:
            body["description"] = description
        if all_day is not None:
            body["all_day"] = all_day
        if status is not None:
            body["status"] = status
        if metadata is not None:
            body["metadata"] = metadata
        if reminders is not None:
            body["reminders"] = reminders
        if hold_expires_at is not None:
            body["hold_expires_at"] = hold_expires_at
        if hold_priority is not None:
            body["hold_priority"] = hold_priority
        resp = await self._request("POST", path, json=body, max_retries=max_retries)
        return self._build(Event, resp)

    async def list(
        self,
        calendar_id: str,
        *,
        start_after: str | None = None,
        start_before: str | None = None,
        status: EventStatus | None = None,
        source: Literal["internal", "external_ical"] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> AsyncPager[Event]:
        path = _EVENTS_PATH.format(calendar_id=calendar_id)
        params: dict[str, Any] = {
            "start_after": start_after,
            "start_before": start_before,
            "status": status,
            "source": source,
            "limit": limit,
            "offset": offset,
        }
        resp = await self._request("GET", path, params=params, max_retries=max_retries)
        raw = resp.json()
        list_resp = ListResponse[Event](
            data=[Event.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return AsyncPager(
            list_resp,
            client=self._client,
            path=path,
            params=params,
            model=Event,
            request_id=resp.headers.get("X-Request-Id"),
        )

    async def get(
        self,
        calendar_id: str,
        event_id: str,
        *,
        max_retries: int | None = None,
    ) -> Event:
        path = f"{_EVENTS_PATH.format(calendar_id=calendar_id)}/{event_id}"
        resp = await self._request("GET", path, max_retries=max_retries)
        return self._build(Event, resp)

    async def update(
        self,
        calendar_id: str,
        event_id: str,
        *,
        title: str | None = None,
        description: str | None = _UNSET,  # type: ignore[assignment]
        start_time: str | None = None,
        end_time: str | None = None,
        all_day: bool | None = None,
        status: Literal["confirmed", "tentative", "cancelled"] | None = None,
        metadata: dict[str, Any] | None = None,
        reminders: list[int] | None = _UNSET,  # type: ignore[assignment]
        max_retries: int | None = None,
    ) -> Event:
        path = f"{_EVENTS_PATH.format(calendar_id=calendar_id)}/{event_id}"
        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = title
        if description is not _UNSET:
            body["description"] = description
        if start_time is not None:
            body["start_time"] = start_time
        if end_time is not None:
            body["end_time"] = end_time
        if all_day is not None:
            body["all_day"] = all_day
        if status is not None:
            body["status"] = status
        if metadata is not None:
            body["metadata"] = metadata
        if reminders is not _UNSET:
            body["reminders"] = reminders
        resp = await self._request("PATCH", path, json=body, max_retries=max_retries)
        return self._build(Event, resp)

    async def delete(
        self,
        calendar_id: str,
        event_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        path = f"{_EVENTS_PATH.format(calendar_id=calendar_id)}/{event_id}"
        await self._request("DELETE", path, max_retries=max_retries)

    async def get_by_id(
        self,
        event_id: str,
        *,
        max_retries: int | None = None,
    ) -> Event:
        """Fetch an event by ID alone — the calendar is resolved internally."""
        path = _EVENT_BY_ID_PATH.format(event_id=event_id)
        resp = await self._request("GET", path, max_retries=max_retries)
        return self._build(Event, resp)

    async def update_by_id(
        self,
        event_id: str,
        *,
        title: str | None = None,
        description: str | None = _UNSET,  # type: ignore[assignment]
        start_time: str | None = None,
        end_time: str | None = None,
        all_day: bool | None = None,
        status: Literal["confirmed", "tentative", "cancelled"] | None = None,
        metadata: dict[str, Any] | None = None,
        reminders: list[int] | None = _UNSET,  # type: ignore[assignment]
        max_retries: int | None = None,
    ) -> Event:
        """Update an event by ID alone — the calendar is resolved internally."""
        path = _EVENT_BY_ID_PATH.format(event_id=event_id)
        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = title
        if description is not _UNSET:
            body["description"] = description
        if start_time is not None:
            body["start_time"] = start_time
        if end_time is not None:
            body["end_time"] = end_time
        if all_day is not None:
            body["all_day"] = all_day
        if status is not None:
            body["status"] = status
        if metadata is not None:
            body["metadata"] = metadata
        if reminders is not _UNSET:
            body["reminders"] = reminders
        resp = await self._request("PATCH", path, json=body, max_retries=max_retries)
        return self._build(Event, resp)

    async def delete_by_id(
        self,
        event_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        """Delete an event by ID alone — the calendar is resolved internally."""
        path = _EVENT_BY_ID_PATH.format(event_id=event_id)
        await self._request("DELETE", path, max_retries=max_retries)

    async def confirm(
        self,
        event_id: str,
        *,
        max_retries: int | None = None,
    ) -> Event:
        """Promote a held event (status='hold') to status='confirmed'."""
        path = _EVENTS_CONFIRM_PATH.format(event_id=event_id)
        resp = await self._request("PUT", path, max_retries=max_retries)
        return self._build(Event, resp)

    async def release(
        self,
        event_id: str,
        *,
        max_retries: int | None = None,
    ) -> Event:
        """Manually release a held event before its TTL, freeing the slot."""
        path = _EVENTS_RELEASE_PATH.format(event_id=event_id)
        resp = await self._request("PUT", path, max_retries=max_retries)
        return self._build(Event, resp)


# ---------------------------------------------------------------------------
# Sync agent-scoped sub-resource
# ---------------------------------------------------------------------------

_AGENT_EVENTS_PATH = "/v1/agents/{agent_id}/events"


class AgentEvents(SyncAPIResource):
    """client.agents.events — agent-scoped event listing."""

    def list(
        self,
        agent_id: str,
        *,
        start_after: str | None = None,
        start_before: str | None = None,
        status: EventStatus | None = None,
        source: Literal["internal", "external_ical"] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> SyncPager[Event]:
        path = _AGENT_EVENTS_PATH.format(agent_id=agent_id)
        params: dict[str, Any] = {
            "start_after": start_after,
            "start_before": start_before,
            "status": status,
            "source": source,
            "limit": limit,
            "offset": offset,
        }
        resp = self._request("GET", path, params=params, max_retries=max_retries)
        raw = resp.json()
        list_resp = ListResponse[Event](
            data=[Event.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return SyncPager(
            list_resp,
            client=self._client,
            path=path,
            params=params,
            model=Event,
            request_id=resp.headers.get("X-Request-Id"),
        )


# ---------------------------------------------------------------------------
# Async agent-scoped sub-resource
# ---------------------------------------------------------------------------


class AsyncAgentEvents(AsyncAPIResource):
    """client.agents.events — async agent-scoped event listing."""

    async def list(
        self,
        agent_id: str,
        *,
        start_after: str | None = None,
        start_before: str | None = None,
        status: EventStatus | None = None,
        source: Literal["internal", "external_ical"] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> AsyncPager[Event]:
        path = _AGENT_EVENTS_PATH.format(agent_id=agent_id)
        params: dict[str, Any] = {
            "start_after": start_after,
            "start_before": start_before,
            "status": status,
            "source": source,
            "limit": limit,
            "offset": offset,
        }
        resp = await self._request("GET", path, params=params, max_retries=max_retries)
        raw = resp.json()
        list_resp = ListResponse[Event](
            data=[Event.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return AsyncPager(
            list_resp,
            client=self._client,
            path=path,
            params=params,
            model=Event,
            request_id=resp.headers.get("X-Request-Id"),
        )
