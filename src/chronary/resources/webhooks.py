from __future__ import annotations

from datetime import datetime  # noqa: TCH003 — Pydantic needs this at runtime
from typing import Any, Literal, Optional

from ..webhook import (
    unwrap as _unwrap,
    verify_signature as _verify_signature,
)

from pydantic import Field
from typing_extensions import Required, TypedDict

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource
from ..pagination import AsyncPager, ListResponse, SyncPager

# ---------------------------------------------------------------------------
# Event types — mirrors packages/shared/src/schemas/webhooks.ts WEBHOOK_EVENT_TYPES
# ---------------------------------------------------------------------------

WebhookEventType = Literal[
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
]

WEBHOOK_EVENT_TYPES: tuple[WebhookEventType, ...] = (
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
)

# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------


class Webhook(ChronaryModel):
    """A webhook subscription."""

    id: str
    org_id: str = Field(alias="orgId")
    url: str
    events: list[WebhookEventType]
    active: bool = True
    secret: str | None = None  # Only present on creation response
    consecutive_failures: int = Field(alias="consecutiveFailures")
    first_failure_at: datetime | None = Field(default=None, alias="firstFailureAt")
    created_at: datetime = Field(alias="createdAt")


DeliveryStatus = Literal["pending", "delivered", "failed"]


class WebhookDelivery(ChronaryModel):
    """A single webhook delivery record."""

    id: str
    subscription_id: str
    event_type: str
    status: DeliveryStatus
    attempts: int
    last_attempt_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    created_at: datetime
    payload: Optional[dict[str, Any]] = None


class WebhookDeliveryStats(ChronaryModel):
    pending: int
    delivered: int
    failed: int


class WebhookDeliveryListResponse(ChronaryModel):
    data: list[WebhookDelivery]
    total: int
    limit: int
    offset: int
    stats: WebhookDeliveryStats


# ---------------------------------------------------------------------------
# Request param TypedDicts
# ---------------------------------------------------------------------------


class WebhookCreateParams(TypedDict):
    url: Required[str]
    events: Required[list[WebhookEventType]]


class WebhookUpdateParams(TypedDict, total=False):
    url: str
    events: list[WebhookEventType]
    active: bool


class WebhookListParams(TypedDict, total=False):
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Sync resource
# ---------------------------------------------------------------------------

_WEBHOOKS_PATH = "/v1/webhooks"


class Webhooks(SyncAPIResource):
    """client.webhooks — synchronous CRUD for webhook subscriptions."""

    def create(
        self,
        *,
        url: str,
        events: list[str],
        max_retries: int | None = None,
    ) -> Webhook:
        body: dict[str, Any] = {"url": url, "events": events}
        resp = self._request("POST", _WEBHOOKS_PATH, json=body, max_retries=max_retries)
        return self._build(Webhook, resp)

    def list(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> SyncPager[Webhook]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        resp = self._request("GET", _WEBHOOKS_PATH, params=params, max_retries=max_retries)
        raw = resp.json()
        list_resp = ListResponse[Webhook](
            data=[Webhook.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return SyncPager(
            list_resp,
            client=self._client,
            path=_WEBHOOKS_PATH,
            params=params,
            model=Webhook,
            request_id=resp.headers.get("X-Request-Id"),
        )

    def get(
        self,
        webhook_id: str,
        *,
        max_retries: int | None = None,
    ) -> Webhook:
        resp = self._request("GET", f"{_WEBHOOKS_PATH}/{webhook_id}", max_retries=max_retries)
        return self._build(Webhook, resp)

    def update(
        self,
        webhook_id: str,
        *,
        url: str | None = None,
        events: list[str] | None = None,
        active: bool | None = None,
        max_retries: int | None = None,
    ) -> Webhook:
        body: dict[str, Any] = {}
        if url is not None:
            body["url"] = url
        if events is not None:
            body["events"] = events
        if active is not None:
            body["active"] = active
        resp = self._request(
            "PATCH", f"{_WEBHOOKS_PATH}/{webhook_id}", json=body, max_retries=max_retries
        )
        return self._build(Webhook, resp)

    def delete(
        self,
        webhook_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        self._request("DELETE", f"{_WEBHOOKS_PATH}/{webhook_id}", max_retries=max_retries)

    def list_deliveries(
        self,
        webhook_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
        status: DeliveryStatus | None = None,
        include_payload: bool | None = None,
        max_retries: int | None = None,
    ) -> WebhookDeliveryListResponse:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if status is not None:
            params["status"] = status
        if include_payload is not None:
            params["include_payload"] = str(include_payload).lower()
        path = f"{_WEBHOOKS_PATH}/{webhook_id}/deliveries"
        resp = self._request("GET", path, params=params, max_retries=max_retries)
        return WebhookDeliveryListResponse.model_validate(resp.json())

    @staticmethod
    def verify_signature(
        payload: bytes | str,
        headers: Any,
        *,
        secret: str,
        tolerance: int = 300,
    ) -> None:
        """Verify an incoming webhook's signature. See chronary.webhook.verify_signature."""
        _verify_signature(payload, headers, secret=secret, tolerance=tolerance)

    @staticmethod
    def unwrap(
        payload: bytes | str,
        headers: Any,
        *,
        secret: str,
        tolerance: int = 300,
    ) -> dict[str, Any]:
        """Verify + parse a webhook payload. See chronary.webhook.unwrap."""
        return _unwrap(payload, headers, secret=secret, tolerance=tolerance)


# ---------------------------------------------------------------------------
# Async resource
# ---------------------------------------------------------------------------


class AsyncWebhooks(AsyncAPIResource):
    """client.webhooks — asynchronous CRUD for webhook subscriptions."""

    async def create(
        self,
        *,
        url: str,
        events: list[str],
        max_retries: int | None = None,
    ) -> Webhook:
        body: dict[str, Any] = {"url": url, "events": events}
        resp = await self._request("POST", _WEBHOOKS_PATH, json=body, max_retries=max_retries)
        return self._build(Webhook, resp)

    async def list(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> AsyncPager[Webhook]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        resp = await self._request(
            "GET", _WEBHOOKS_PATH, params=params, max_retries=max_retries
        )
        raw = resp.json()
        list_resp = ListResponse[Webhook](
            data=[Webhook.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return AsyncPager(
            list_resp,
            client=self._client,
            path=_WEBHOOKS_PATH,
            params=params,
            model=Webhook,
            request_id=resp.headers.get("X-Request-Id"),
        )

    async def get(
        self,
        webhook_id: str,
        *,
        max_retries: int | None = None,
    ) -> Webhook:
        resp = await self._request(
            "GET", f"{_WEBHOOKS_PATH}/{webhook_id}", max_retries=max_retries
        )
        return self._build(Webhook, resp)

    async def update(
        self,
        webhook_id: str,
        *,
        url: str | None = None,
        events: list[str] | None = None,
        active: bool | None = None,
        max_retries: int | None = None,
    ) -> Webhook:
        body: dict[str, Any] = {}
        if url is not None:
            body["url"] = url
        if events is not None:
            body["events"] = events
        if active is not None:
            body["active"] = active
        resp = await self._request(
            "PATCH", f"{_WEBHOOKS_PATH}/{webhook_id}", json=body, max_retries=max_retries
        )
        return self._build(Webhook, resp)

    async def delete(
        self,
        webhook_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        await self._request(
            "DELETE", f"{_WEBHOOKS_PATH}/{webhook_id}", max_retries=max_retries
        )

    async def list_deliveries(
        self,
        webhook_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
        status: DeliveryStatus | None = None,
        include_payload: bool | None = None,
        max_retries: int | None = None,
    ) -> WebhookDeliveryListResponse:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if status is not None:
            params["status"] = status
        if include_payload is not None:
            params["include_payload"] = str(include_payload).lower()
        path = f"{_WEBHOOKS_PATH}/{webhook_id}/deliveries"
        resp = await self._request("GET", path, params=params, max_retries=max_retries)
        return WebhookDeliveryListResponse.model_validate(resp.json())

    @staticmethod
    def verify_signature(
        payload: bytes | str,
        headers: Any,
        *,
        secret: str,
        tolerance: int = 300,
    ) -> None:
        """Verify an incoming webhook's signature. See chronary.webhook.verify_signature."""
        _verify_signature(payload, headers, secret=secret, tolerance=tolerance)

    @staticmethod
    def unwrap(
        payload: bytes | str,
        headers: Any,
        *,
        secret: str,
        tolerance: int = 300,
    ) -> dict[str, Any]:
        """Verify + parse a webhook payload. See chronary.webhook.unwrap."""
        return _unwrap(payload, headers, secret=secret, tolerance=tolerance)
