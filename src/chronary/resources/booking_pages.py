from __future__ import annotations

from datetime import datetime  # noqa: TCH003 — Pydantic needs this at runtime
from typing import Any

from typing_extensions import NotRequired, Required, TypedDict

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource
from ..pagination import AsyncPager, ListResponse, SyncPager

# Sentinel for distinguishing "not passed" from "explicitly passed None"
_UNSET: Any = object()

_BOOKING_PAGES_PATH = "/v1/booking-pages"


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------


class BookingPage(ChronaryModel):
    """A public booking page (a hosted scheduling link)."""

    id: str
    org_id: str
    calendar_id: str
    agent_id: str | None = None
    slug: str
    title: str
    description: str | None = None
    duration_minutes: int
    buffer_minutes: int
    window_days: int
    min_notice_minutes: int
    timezone: str
    availability_constraints: dict[str, Any] | None = None
    active: bool
    bookings_count: int
    booking_url: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Request param TypedDicts
# ---------------------------------------------------------------------------


class WorkingHoursDay(TypedDict):
    start: Required[str]
    end: Required[str]


class BookingPageCreateParams(TypedDict):
    calendar_id: Required[str]
    title: Required[str]
    description: NotRequired[str]
    duration_minutes: NotRequired[int]
    buffer_minutes: NotRequired[int]
    window_days: NotRequired[int]
    min_notice_minutes: NotRequired[int]
    timezone: NotRequired[str]
    availability_constraints: NotRequired[dict[str, WorkingHoursDay] | None]
    active: NotRequired[bool]


class BookingPageUpdateParams(TypedDict, total=False):
    title: str
    description: str | None
    duration_minutes: int
    buffer_minutes: int
    window_days: int
    min_notice_minutes: int
    timezone: str
    availability_constraints: dict[str, WorkingHoursDay] | None
    active: bool


class BookingPageListParams(TypedDict, total=False):
    limit: int
    offset: int


def _create_body(
    calendar_id: str,
    title: str,
    description: str | None,
    duration_minutes: int | None,
    buffer_minutes: int | None,
    window_days: int | None,
    min_notice_minutes: int | None,
    timezone: str | None,
    availability_constraints: Any,
    active: bool | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"calendar_id": calendar_id, "title": title}
    if description is not None:
        body["description"] = description
    if duration_minutes is not None:
        body["duration_minutes"] = duration_minutes
    if buffer_minutes is not None:
        body["buffer_minutes"] = buffer_minutes
    if window_days is not None:
        body["window_days"] = window_days
    if min_notice_minutes is not None:
        body["min_notice_minutes"] = min_notice_minutes
    if timezone is not None:
        body["timezone"] = timezone
    if availability_constraints is not _UNSET:
        body["availability_constraints"] = availability_constraints
    if active is not None:
        body["active"] = active
    return body


def _update_body(
    title: str | None,
    description: Any,
    duration_minutes: int | None,
    buffer_minutes: int | None,
    window_days: int | None,
    min_notice_minutes: int | None,
    timezone: str | None,
    availability_constraints: Any,
    active: bool | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if title is not None:
        body["title"] = title
    if description is not _UNSET:
        body["description"] = description
    if duration_minutes is not None:
        body["duration_minutes"] = duration_minutes
    if buffer_minutes is not None:
        body["buffer_minutes"] = buffer_minutes
    if window_days is not None:
        body["window_days"] = window_days
    if min_notice_minutes is not None:
        body["min_notice_minutes"] = min_notice_minutes
    if timezone is not None:
        body["timezone"] = timezone
    if availability_constraints is not _UNSET:
        body["availability_constraints"] = availability_constraints
    if active is not None:
        body["active"] = active
    return body


# ---------------------------------------------------------------------------
# Sync resource
# ---------------------------------------------------------------------------


class BookingPages(SyncAPIResource):
    """client.booking_pages — synchronous CRUD for public booking pages."""

    def create(
        self,
        *,
        calendar_id: str,
        title: str,
        description: str | None = None,
        duration_minutes: int | None = None,
        buffer_minutes: int | None = None,
        window_days: int | None = None,
        min_notice_minutes: int | None = None,
        timezone: str | None = None,
        availability_constraints: dict[str, Any] | None = _UNSET,  # type: ignore[assignment]
        active: bool | None = None,
        max_retries: int | None = None,
    ) -> BookingPage:
        body = _create_body(
            calendar_id, title, description, duration_minutes, buffer_minutes,
            window_days, min_notice_minutes, timezone, availability_constraints, active,
        )
        resp = self._request("POST", _BOOKING_PAGES_PATH, json=body, max_retries=max_retries)
        return self._build(BookingPage, resp)

    def list(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> SyncPager[BookingPage]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        resp = self._request("GET", _BOOKING_PAGES_PATH, params=params, max_retries=max_retries)
        raw = resp.json()
        list_resp = ListResponse[BookingPage](
            data=[BookingPage.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return SyncPager(
            list_resp,
            client=self._client,
            path=_BOOKING_PAGES_PATH,
            params=params,
            model=BookingPage,
            request_id=resp.headers.get("X-Request-Id"),
        )

    def get(self, booking_page_id: str, *, max_retries: int | None = None) -> BookingPage:
        resp = self._request("GET", f"{_BOOKING_PAGES_PATH}/{booking_page_id}", max_retries=max_retries)
        return self._build(BookingPage, resp)

    def update(
        self,
        booking_page_id: str,
        *,
        title: str | None = None,
        description: str | None = _UNSET,  # type: ignore[assignment]
        duration_minutes: int | None = None,
        buffer_minutes: int | None = None,
        window_days: int | None = None,
        min_notice_minutes: int | None = None,
        timezone: str | None = None,
        availability_constraints: dict[str, Any] | None = _UNSET,  # type: ignore[assignment]
        active: bool | None = None,
        max_retries: int | None = None,
    ) -> BookingPage:
        body = _update_body(
            title, description, duration_minutes, buffer_minutes, window_days,
            min_notice_minutes, timezone, availability_constraints, active,
        )
        resp = self._request(
            "PATCH", f"{_BOOKING_PAGES_PATH}/{booking_page_id}", json=body, max_retries=max_retries
        )
        return self._build(BookingPage, resp)

    def delete(self, booking_page_id: str, *, max_retries: int | None = None) -> None:
        self._request("DELETE", f"{_BOOKING_PAGES_PATH}/{booking_page_id}", max_retries=max_retries)


# ---------------------------------------------------------------------------
# Async resource
# ---------------------------------------------------------------------------


class AsyncBookingPages(AsyncAPIResource):
    """client.booking_pages — asynchronous CRUD for public booking pages."""

    async def create(
        self,
        *,
        calendar_id: str,
        title: str,
        description: str | None = None,
        duration_minutes: int | None = None,
        buffer_minutes: int | None = None,
        window_days: int | None = None,
        min_notice_minutes: int | None = None,
        timezone: str | None = None,
        availability_constraints: dict[str, Any] | None = _UNSET,  # type: ignore[assignment]
        active: bool | None = None,
        max_retries: int | None = None,
    ) -> BookingPage:
        body = _create_body(
            calendar_id, title, description, duration_minutes, buffer_minutes,
            window_days, min_notice_minutes, timezone, availability_constraints, active,
        )
        resp = await self._request("POST", _BOOKING_PAGES_PATH, json=body, max_retries=max_retries)
        return self._build(BookingPage, resp)

    async def list(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> AsyncPager[BookingPage]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        resp = await self._request("GET", _BOOKING_PAGES_PATH, params=params, max_retries=max_retries)
        raw = resp.json()
        list_resp = ListResponse[BookingPage](
            data=[BookingPage.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return AsyncPager(
            list_resp,
            client=self._client,
            path=_BOOKING_PAGES_PATH,
            params=params,
            model=BookingPage,
            request_id=resp.headers.get("X-Request-Id"),
        )

    async def get(self, booking_page_id: str, *, max_retries: int | None = None) -> BookingPage:
        resp = await self._request(
            "GET", f"{_BOOKING_PAGES_PATH}/{booking_page_id}", max_retries=max_retries
        )
        return self._build(BookingPage, resp)

    async def update(
        self,
        booking_page_id: str,
        *,
        title: str | None = None,
        description: str | None = _UNSET,  # type: ignore[assignment]
        duration_minutes: int | None = None,
        buffer_minutes: int | None = None,
        window_days: int | None = None,
        min_notice_minutes: int | None = None,
        timezone: str | None = None,
        availability_constraints: dict[str, Any] | None = _UNSET,  # type: ignore[assignment]
        active: bool | None = None,
        max_retries: int | None = None,
    ) -> BookingPage:
        body = _update_body(
            title, description, duration_minutes, buffer_minutes, window_days,
            min_notice_minutes, timezone, availability_constraints, active,
        )
        resp = await self._request(
            "PATCH", f"{_BOOKING_PAGES_PATH}/{booking_page_id}", json=body, max_retries=max_retries
        )
        return self._build(BookingPage, resp)

    async def delete(self, booking_page_id: str, *, max_retries: int | None = None) -> None:
        await self._request(
            "DELETE", f"{_BOOKING_PAGES_PATH}/{booking_page_id}", max_retries=max_retries
        )
