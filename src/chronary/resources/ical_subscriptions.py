from __future__ import annotations

from datetime import datetime  # noqa: TCH003 — Pydantic needs this at runtime
from typing import Any, Literal

from typing_extensions import NotRequired, Required, TypedDict

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource
from ..pagination import AsyncPager, ListResponse, SyncPager

# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------


class ICalSubscription(ChronaryModel):
    """An iCal feed subscription that imports events into a calendar."""

    id: str
    agent_id: str
    calendar_id: str
    url: str
    label: str | None = None
    status: Literal["active", "error", "paused"] = "active"
    last_synced_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Request param TypedDicts
# ---------------------------------------------------------------------------


class ICalSubscriptionCreateParams(TypedDict):
    calendar_id: Required[str]
    url: Required[str]
    label: NotRequired[str]


class ICalSubscriptionUpdateParams(TypedDict, total=False):
    label: str
    url: str


class ICalSubscriptionListParams(TypedDict, total=False):
    status: Literal["active", "error", "paused"]
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Sync resource
# ---------------------------------------------------------------------------

_AGENT_ICAL_PATH = "/v1/agents/{agent_id}/ical-subscriptions"
_ICAL_PATH = "/v1/ical-subscriptions"


class ICalSubscriptions(SyncAPIResource):
    """client.ical_subscriptions — synchronous CRUD for iCal subscriptions."""

    def create(
        self,
        agent_id: str,
        *,
        calendar_id: str,
        url: str,
        label: str | None = None,
        max_retries: int | None = None,
    ) -> ICalSubscription:
        path = _AGENT_ICAL_PATH.format(agent_id=agent_id)
        body: dict[str, Any] = {"calendar_id": calendar_id, "url": url}
        if label is not None:
            body["label"] = label
        resp = self._request("POST", path, json=body, max_retries=max_retries)
        return self._build(ICalSubscription, resp)

    def list(
        self,
        agent_id: str,
        *,
        status: Literal["active", "error", "paused"] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> SyncPager[ICalSubscription]:
        path = _AGENT_ICAL_PATH.format(agent_id=agent_id)
        params: dict[str, Any] = {
            "status": status,
            "limit": limit,
            "offset": offset,
        }
        resp = self._request("GET", path, params=params, max_retries=max_retries)
        raw = resp.json()
        list_resp = ListResponse[ICalSubscription](
            data=[ICalSubscription.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return SyncPager(
            list_resp,
            client=self._client,
            path=path,
            params=params,
            model=ICalSubscription,
            request_id=resp.headers.get("X-Request-Id"),
        )

    def get(
        self,
        subscription_id: str,
        *,
        max_retries: int | None = None,
    ) -> ICalSubscription:
        resp = self._request(
            "GET", f"{_ICAL_PATH}/{subscription_id}", max_retries=max_retries
        )
        return self._build(ICalSubscription, resp)

    def update(
        self,
        subscription_id: str,
        *,
        label: str | None = None,
        url: str | None = None,
        max_retries: int | None = None,
    ) -> ICalSubscription:
        body: dict[str, Any] = {}
        if label is not None:
            body["label"] = label
        if url is not None:
            body["url"] = url
        resp = self._request(
            "PATCH", f"{_ICAL_PATH}/{subscription_id}", json=body, max_retries=max_retries
        )
        return self._build(ICalSubscription, resp)

    def delete(
        self,
        subscription_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        self._request("DELETE", f"{_ICAL_PATH}/{subscription_id}", max_retries=max_retries)

    def sync(
        self,
        subscription_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        self._request(
            "POST", f"{_ICAL_PATH}/{subscription_id}/sync", max_retries=max_retries
        )


# ---------------------------------------------------------------------------
# Async resource
# ---------------------------------------------------------------------------


class AsyncICalSubscriptions(AsyncAPIResource):
    """client.ical_subscriptions — asynchronous CRUD for iCal subscriptions."""

    async def create(
        self,
        agent_id: str,
        *,
        calendar_id: str,
        url: str,
        label: str | None = None,
        max_retries: int | None = None,
    ) -> ICalSubscription:
        path = _AGENT_ICAL_PATH.format(agent_id=agent_id)
        body: dict[str, Any] = {"calendar_id": calendar_id, "url": url}
        if label is not None:
            body["label"] = label
        resp = await self._request("POST", path, json=body, max_retries=max_retries)
        return self._build(ICalSubscription, resp)

    async def list(
        self,
        agent_id: str,
        *,
        status: Literal["active", "error", "paused"] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> AsyncPager[ICalSubscription]:
        path = _AGENT_ICAL_PATH.format(agent_id=agent_id)
        params: dict[str, Any] = {
            "status": status,
            "limit": limit,
            "offset": offset,
        }
        resp = await self._request("GET", path, params=params, max_retries=max_retries)
        raw = resp.json()
        list_resp = ListResponse[ICalSubscription](
            data=[ICalSubscription.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return AsyncPager(
            list_resp,
            client=self._client,
            path=path,
            params=params,
            model=ICalSubscription,
            request_id=resp.headers.get("X-Request-Id"),
        )

    async def get(
        self,
        subscription_id: str,
        *,
        max_retries: int | None = None,
    ) -> ICalSubscription:
        resp = await self._request(
            "GET", f"{_ICAL_PATH}/{subscription_id}", max_retries=max_retries
        )
        return self._build(ICalSubscription, resp)

    async def update(
        self,
        subscription_id: str,
        *,
        label: str | None = None,
        url: str | None = None,
        max_retries: int | None = None,
    ) -> ICalSubscription:
        body: dict[str, Any] = {}
        if label is not None:
            body["label"] = label
        if url is not None:
            body["url"] = url
        resp = await self._request(
            "PATCH", f"{_ICAL_PATH}/{subscription_id}", json=body, max_retries=max_retries
        )
        return self._build(ICalSubscription, resp)

    async def delete(
        self,
        subscription_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        await self._request(
            "DELETE", f"{_ICAL_PATH}/{subscription_id}", max_retries=max_retries
        )

    async def sync(
        self,
        subscription_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        await self._request(
            "POST", f"{_ICAL_PATH}/{subscription_id}/sync", max_retries=max_retries
        )
