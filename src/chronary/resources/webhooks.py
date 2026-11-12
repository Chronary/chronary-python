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
    "org.plan_changed",
    "calendar_connection.reauthorization_required",
    "usage.threshold_crossed",
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
    "org.plan_changed",
    "calendar_connection.reauthorization_required",
    "usage.threshold_crossed",
)

# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------


# Why a webhook endpoint is inactive.
WebhookDeactivatedReason = Literal[
    "manual",
    "circuit_breaker",
    "unsafe_destination_url",
    "account_deletion",
]


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
    # Set while a scheduled account deletion has paused this endpoint.
    deletion_paused_at: datetime | None = Field(default=None, alias="deletionPausedAt")
    # When and why the endpoint last went inactive; None while it is active.
    deactivated_at: datetime | None = Field(default=None, alias="deactivatedAt")
    deactivated_reason: WebhookDeactivatedReason | None = Field(
        default=None, alias="deactivatedReason"
    )
    # While a secret rotation's grace window is open, when the replaced secret
    # stops working (deliveries also carry ``X-Signature-Previous`` until then).
    previous_secret_expires_at: datetime | None = Field(
        default=None, alias="previousSecretExpiresAt"
    )
    created_at: datetime = Field(alias="createdAt")


# ``dropped``: a Free-plan delivery the monthly limit stopped (never sent,
# counted or retried; ``last_error_code`` is "quota_exceeded").
DeliveryStatus = Literal["pending", "delivered", "failed", "dropped"]


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
    # Outcome of the most recent attempt; None before the first attempt.
    last_response_status: int | None = None
    last_error_code: str | None = None
    last_duration_ms: int | None = None
    # True for a test event sent with ``webhooks.send_test``.
    is_test: bool = False
    # Set on a replay (``webhooks.replay_delivery``): the first delivery of the
    # chain, the original even when a replay is replayed. None otherwise.
    replay_of_delivery_id: str | None = None
    payload: dict[str, Any | None] = None


# Why one delivery attempt failed. A delivery's ``last_error_code`` may also be
# "endpoint_disabled" or "quota_exceeded".
WebhookAttemptErrorCode = Literal[
    "timeout",
    "connection_error",
    "tls_error",
    "redirect_not_followed",
    "unsafe_destination_url",
    "non_2xx",
]


class WebhookDeliveryAttempt(ChronaryModel):
    """One HTTP attempt of a webhook delivery."""

    id: str
    attempt_number: int
    started_at: datetime
    duration_ms: int | None = None
    response_status: int | None = None
    response_body: str | None = None
    error_code: str | None = None


class WebhookDeliveryDetail(ChronaryModel):
    """One webhook delivery with its payload and every attempt, oldest first."""

    id: str
    subscription_id: str
    event_type: str
    status: DeliveryStatus
    attempts: int
    max_attempts: int
    last_attempt_at: datetime | None = None
    next_retry_at: datetime | None = None
    created_at: datetime
    last_response_status: int | None = None
    last_error_code: str | None = None
    last_duration_ms: int | None = None
    is_test: bool = False
    replay_of_delivery_id: str | None = None
    payload: Any = None
    payload_redacted: bool = False
    request_headers: dict[str, str] = Field(default_factory=dict)
    attempt_log: list[WebhookDeliveryAttempt] = Field(default_factory=list)


class WebhookTestSent(ChronaryModel):
    """The queued test delivery returned by ``webhooks.send_test``."""

    delivery_id: str
    webhook_id: str
    event_type: str
    status: Literal["pending"]
    is_test: bool


class WebhookReplaySent(ChronaryModel):
    """The new delivery returned by ``webhooks.replay_delivery``."""

    delivery_id: str
    webhook_id: str
    event_type: str
    status: Literal["pending"]
    # The first delivery of the chain, sent as ``X-Chronary-Replay-Of``.
    replay_of_delivery_id: str


# When the replaced secret stops working after ``webhooks.rotate_secret``.
WebhookSecretExpiry = Literal["now", "1h", "24h", "7d"]


class RotatedWebhookSecret(ChronaryModel):
    """The new signing secret returned once by ``webhooks.rotate_secret``."""

    webhook_id: str
    secret: str
    # When the replaced secret stops working; None when ``expire_old_in`` was "now".
    previous_secret_expires_at: datetime | None = None


class WebhookDeliveryStats(ChronaryModel):
    pending: int
    delivered: int
    failed: int
    # Deliveries the Free plan monthly limit stopped.
    dropped: int = 0


class WebhookDeliveryListResponse(ChronaryModel):
    data: list[WebhookDelivery]
    # Deliveries matching the filters, ignoring the cursor and offset.
    total: int
    limit: int
    offset: int
    # Pass as ``cursor`` for the next page; None on the last page.
    next_cursor: str | None = None
    has_more: bool = False
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
        event_type: str | None = None,
        created_after: str | None = None,
        created_before: str | None = None,
        delivery_id: str | None = None,
        is_test: bool | None = None,
        cursor: str | None = None,
        max_retries: int | None = None,
    ) -> WebhookDeliveryListResponse:
        """Deliveries newest first. ``event_type`` is exact (``event.created``)
        or a prefix ending in a dot (``event.``). Page with ``cursor`` (the
        previous page's ``next_cursor``); it cannot be combined with a non-zero
        ``offset``."""
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if status is not None:
            params["status"] = status
        if include_payload is not None:
            params["include_payload"] = str(include_payload).lower()
        if event_type is not None:
            params["event_type"] = event_type
        if created_after is not None:
            params["created_after"] = created_after
        if created_before is not None:
            params["created_before"] = created_before
        if delivery_id is not None:
            params["delivery_id"] = delivery_id
        if is_test is not None:
            params["is_test"] = str(is_test).lower()
        if cursor is not None:
            params["cursor"] = cursor
        path = f"{_WEBHOOKS_PATH}/{webhook_id}/deliveries"
        resp = self._request("GET", path, params=params, max_retries=max_retries)
        return WebhookDeliveryListResponse.model_validate(resp.json())

    def get_delivery(
        self,
        webhook_id: str,
        delivery_id: str,
        *,
        max_retries: int | None = None,
    ) -> WebhookDeliveryDetail:
        """One delivery with its payload and every attempt, oldest first."""
        path = f"{_WEBHOOKS_PATH}/{webhook_id}/deliveries/{delivery_id}"
        resp = self._request("GET", path, max_retries=max_retries)
        return WebhookDeliveryDetail.model_validate(resp.json())

    def send_test(
        self,
        webhook_id: str,
        *,
        event_type: WebhookEventType,
        max_retries: int | None = None,
    ) -> WebhookTestSent:
        """Send a signed sample payload of one event type to the endpoint.

        The delivery is marked ``is_test``, carries ``X-Chronary-Test: 1``, makes
        one attempt and does not count toward the monthly quota. Poll
        ``get_delivery`` with the returned ``delivery_id`` for the result.
        """
        path = f"{_WEBHOOKS_PATH}/{webhook_id}/test"
        resp = self._request("POST", path, json={"event_type": event_type}, max_retries=max_retries)
        return WebhookTestSent.model_validate(resp.json())

    def replay_delivery(
        self,
        webhook_id: str,
        delivery_id: str,
        *,
        idempotency_key: str | None = None,
        max_retries: int | None = None,
    ) -> WebhookReplaySent:
        """Send a failed or dropped delivery again as a new delivery (Developer or Pro).

        The stored payload goes out unchanged, signed with the endpoint's
        current secret, with an ``X-Chronary-Replay-Of`` header. The replay
        follows the normal retry schedule and counts toward the monthly delivery
        quota. The endpoint must be active. Poll ``get_delivery`` with the
        returned ``delivery_id`` for the result. Limited to 30 per minute.
        """
        path = f"{_WEBHOOKS_PATH}/{webhook_id}/deliveries/{delivery_id}/replay"
        resp = self._request("POST", path, idempotency_key=idempotency_key, max_retries=max_retries)
        return WebhookReplaySent.model_validate(resp.json())

    def rotate_secret(
        self,
        webhook_id: str,
        *,
        expire_old_in: WebhookSecretExpiry | None = None,
        max_retries: int | None = None,
    ) -> RotatedWebhookSecret:
        """Rotate the endpoint's signing secret (Developer or Pro). Returns the new secret once.

        The new secret signs ``X-Signature`` from the next attempt. The replaced
        secret keeps signing ``X-Signature-Previous`` until ``expire_old_in`` has
        passed: "now", "1h", "24h" (the API default) or "7d". ``verify_signature``
        accepts either header, so receivers can switch secrets in that window.
        """
        path = f"{_WEBHOOKS_PATH}/{webhook_id}/secret/rotate"
        body: dict[str, Any] = {} if expire_old_in is None else {"expire_old_in": expire_old_in}
        resp = self._request("POST", path, json=body, max_retries=max_retries)
        return RotatedWebhookSecret.model_validate(resp.json())

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
        event_type: str | None = None,
        created_after: str | None = None,
        created_before: str | None = None,
        delivery_id: str | None = None,
        is_test: bool | None = None,
        cursor: str | None = None,
        max_retries: int | None = None,
    ) -> WebhookDeliveryListResponse:
        """Deliveries newest first. ``event_type`` is exact (``event.created``)
        or a prefix ending in a dot (``event.``). Page with ``cursor`` (the
        previous page's ``next_cursor``); it cannot be combined with a non-zero
        ``offset``."""
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if status is not None:
            params["status"] = status
        if include_payload is not None:
            params["include_payload"] = str(include_payload).lower()
        if event_type is not None:
            params["event_type"] = event_type
        if created_after is not None:
            params["created_after"] = created_after
        if created_before is not None:
            params["created_before"] = created_before
        if delivery_id is not None:
            params["delivery_id"] = delivery_id
        if is_test is not None:
            params["is_test"] = str(is_test).lower()
        if cursor is not None:
            params["cursor"] = cursor
        path = f"{_WEBHOOKS_PATH}/{webhook_id}/deliveries"
        resp = await self._request("GET", path, params=params, max_retries=max_retries)
        return WebhookDeliveryListResponse.model_validate(resp.json())

    async def get_delivery(
        self,
        webhook_id: str,
        delivery_id: str,
        *,
        max_retries: int | None = None,
    ) -> WebhookDeliveryDetail:
        """One delivery with its payload and every attempt, oldest first."""
        path = f"{_WEBHOOKS_PATH}/{webhook_id}/deliveries/{delivery_id}"
        resp = await self._request("GET", path, max_retries=max_retries)
        return WebhookDeliveryDetail.model_validate(resp.json())

    async def send_test(
        self,
        webhook_id: str,
        *,
        event_type: WebhookEventType,
        max_retries: int | None = None,
    ) -> WebhookTestSent:
        """Send a signed sample payload of one event type to the endpoint.

        The delivery is marked ``is_test``, carries ``X-Chronary-Test: 1``, makes
        one attempt and does not count toward the monthly quota. Poll
        ``get_delivery`` with the returned ``delivery_id`` for the result.
        """
        path = f"{_WEBHOOKS_PATH}/{webhook_id}/test"
        resp = await self._request(
            "POST", path, json={"event_type": event_type}, max_retries=max_retries
        )
        return WebhookTestSent.model_validate(resp.json())

    async def replay_delivery(
        self,
        webhook_id: str,
        delivery_id: str,
        *,
        idempotency_key: str | None = None,
        max_retries: int | None = None,
    ) -> WebhookReplaySent:
        """Send a failed or dropped delivery again as a new delivery (Developer or Pro).

        The stored payload goes out unchanged, signed with the endpoint's
        current secret, with an ``X-Chronary-Replay-Of`` header. The replay
        follows the normal retry schedule and counts toward the monthly delivery
        quota. The endpoint must be active. Poll ``get_delivery`` with the
        returned ``delivery_id`` for the result. Limited to 30 per minute.
        """
        path = f"{_WEBHOOKS_PATH}/{webhook_id}/deliveries/{delivery_id}/replay"
        resp = await self._request(
            "POST", path, idempotency_key=idempotency_key, max_retries=max_retries
        )
        return WebhookReplaySent.model_validate(resp.json())

    async def rotate_secret(
        self,
        webhook_id: str,
        *,
        expire_old_in: WebhookSecretExpiry | None = None,
        max_retries: int | None = None,
    ) -> RotatedWebhookSecret:
        """Rotate the endpoint's signing secret (Developer or Pro). Returns the new secret once.

        The new secret signs ``X-Signature`` from the next attempt. The replaced
        secret keeps signing ``X-Signature-Previous`` until ``expire_old_in`` has
        passed: "now", "1h", "24h" (the API default) or "7d". ``verify_signature``
        accepts either header, so receivers can switch secrets in that window.
        """
        path = f"{_WEBHOOKS_PATH}/{webhook_id}/secret/rotate"
        body: dict[str, Any] = {} if expire_old_in is None else {"expire_old_in": expire_old_in}
        resp = await self._request("POST", path, json=body, max_retries=max_retries)
        return RotatedWebhookSecret.model_validate(resp.json())

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
