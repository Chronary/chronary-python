from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource

if TYPE_CHECKING:
    from .._base_client import AsyncAPIClient, SyncAPIClient

# ---------------------------------------------------------------------------
# Response models
#
# Billing is read-only for agents. Agents cannot pay, cancel, or change payment
# methods; they ask a human to upgrade via an upgrade request and hand over its
# ``approval_url``.
# ---------------------------------------------------------------------------

BillingInterval = Literal["month", "year"]
UpgradeRequestStatus = Literal["pending", "completed", "declined", "canceled", "expired"]
OwnerNotification = Literal[
    "queued", "not_configured", "skipped_internal", "already_notified", "muted"
]


class BillingPrice(ChronaryModel):
    amount: int  # minor units (2900 = $29)
    currency: str
    interval: BillingInterval
    tax_exclusive: bool


class BillingUpgradeOption(ChronaryModel):
    plan: str
    interval: BillingInterval
    amount: int
    currency: str
    savings_vs_monthly: int
    # How the owner buys it: "checkout" (no live subscription) or "switch_plan"
    # (a live subscriber moves up from the console Billing page).
    via: str | None = None


class UpgradeRequest(ChronaryModel):
    id: str
    status: UpgradeRequestStatus
    plan: str
    interval: BillingInterval
    # Agent free text — render as escaped plain text only.
    reason: str | None = None
    feature: str | None = None
    metric: str | None = None
    requested_via: Literal["api", "mcp"]
    # First 20 chars of the requesting key, never the full key.
    requested_by_key_prefix: str | None = None
    # Give this URL to your human. None once the request is terminal.
    approval_url: str | None = None
    created_at: str
    expires_at: str
    completed_at: str | None = None
    declined_at: str | None = None
    canceled_at: str | None = None
    # Create responses only.
    owner_notification: OwnerNotification | None = None
    reused: bool | None = None


class BillingPastDue(ChronaryModel):
    """The failed payment behind a past_due subscription."""

    amount_due: int  # minor units (cents), tax included
    currency: str
    failed_at: str
    next_payment_attempt: str | None = None  # None when no retries are left
    hosted_invoice_url: str | None = None
    attempt_count: int


class BillingCredit(ChronaryModel):
    """Account credit, applied to the next invoices while the subscription renews."""

    amount: int  # minor units (cents), always positive
    currency: str


class BillingSummary(ChronaryModel):
    plan: str
    plan_source: str | None = None
    plan_expires_at: str | None = None
    status: str | None = None
    interval: BillingInterval | None = None
    current_period_end: str | None = None
    cancel_at: str | None = None
    cancel_at_period_end: bool
    renews_at: str | None = None
    # A plan switch scheduled for the end of the period (Pro down to Developer).
    pending_plan: str | None = None
    pending_plan_interval: BillingInterval | None = None
    pending_plan_at: str | None = None
    price: BillingPrice | None = None
    has_billing_account: bool
    self_serve_upgrade: bool
    upgrade_options: list[BillingUpgradeOption]
    upgrade_url: str | None = None
    manage_url: str
    contact_url: str | None = None
    pending_upgrade_request: UpgradeRequest | None = None
    offer: Any | None = None
    # While status is past_due: the failed payment. None otherwise.
    past_due: BillingPastDue | None = None
    # Account credit (e.g. after a switch from yearly to monthly). None when there is none.
    credit: BillingCredit | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BILLING_PATH = "/v1/billing"
_UPGRADE_REQUESTS_PATH = "/v1/billing/upgrade-requests"


def _create_body(
    interval: BillingInterval | None,
    reason: str | None,
    feature: str | None,
    metric: str | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if interval is not None:
        body["interval"] = interval
    if reason is not None:
        body["reason"] = reason
    if feature is not None:
        body["feature"] = feature
    if metric is not None:
        body["metric"] = metric
    return body


# ---------------------------------------------------------------------------
# Sync resources
# ---------------------------------------------------------------------------


class UpgradeRequests(SyncAPIResource):
    """client.billing.upgrade_requests — ask a human to upgrade the account."""

    def create(
        self,
        *,
        interval: BillingInterval | None = None,
        reason: str | None = None,
        feature: str | None = None,
        metric: str | None = None,
        idempotency_key: str | None = None,
        max_retries: int | None = None,
    ) -> UpgradeRequest:
        """Create (or reuse the pending) upgrade request. Org keys only.

        Give the returned ``approval_url`` to your human; only a human can pay.
        """
        resp = self._request(
            "POST", _UPGRADE_REQUESTS_PATH,
            json=_create_body(interval, reason, feature, metric),
            idempotency_key=idempotency_key,
            max_retries=max_retries,
        )
        return self._build(UpgradeRequest, resp)

    def get(self, request_id: str, *, max_retries: int | None = None) -> UpgradeRequest:
        resp = self._request(
            "GET", f"{_UPGRADE_REQUESTS_PATH}/{request_id}",
            max_retries=max_retries,
        )
        return self._build(UpgradeRequest, resp)

    def cancel(self, request_id: str, *, max_retries: int | None = None) -> UpgradeRequest:
        resp = self._request(
            "POST", f"{_UPGRADE_REQUESTS_PATH}/{request_id}/cancel",
            max_retries=max_retries,
        )
        return self._build(UpgradeRequest, resp)


class Billing(SyncAPIResource):
    """client.billing — read-only billing summary and upgrade requests."""

    upgrade_requests: UpgradeRequests

    def __init__(self, client: SyncAPIClient) -> None:
        super().__init__(client)
        self.upgrade_requests = UpgradeRequests(client)

    def get(self, *, max_retries: int | None = None) -> BillingSummary:
        resp = self._request("GET", _BILLING_PATH, max_retries=max_retries)
        return self._build(BillingSummary, resp)


# ---------------------------------------------------------------------------
# Async resources
# ---------------------------------------------------------------------------


class AsyncUpgradeRequests(AsyncAPIResource):
    """client.billing.upgrade_requests — ask a human to upgrade the account."""

    async def create(
        self,
        *,
        interval: BillingInterval | None = None,
        reason: str | None = None,
        feature: str | None = None,
        metric: str | None = None,
        idempotency_key: str | None = None,
        max_retries: int | None = None,
    ) -> UpgradeRequest:
        """Create (or reuse the pending) upgrade request. Org keys only.

        Give the returned ``approval_url`` to your human; only a human can pay.
        """
        resp = await self._request(
            "POST", _UPGRADE_REQUESTS_PATH,
            json=_create_body(interval, reason, feature, metric),
            idempotency_key=idempotency_key,
            max_retries=max_retries,
        )
        return self._build(UpgradeRequest, resp)

    async def get(self, request_id: str, *, max_retries: int | None = None) -> UpgradeRequest:
        resp = await self._request(
            "GET", f"{_UPGRADE_REQUESTS_PATH}/{request_id}",
            max_retries=max_retries,
        )
        return self._build(UpgradeRequest, resp)

    async def cancel(self, request_id: str, *, max_retries: int | None = None) -> UpgradeRequest:
        resp = await self._request(
            "POST", f"{_UPGRADE_REQUESTS_PATH}/{request_id}/cancel",
            max_retries=max_retries,
        )
        return self._build(UpgradeRequest, resp)


class AsyncBilling(AsyncAPIResource):
    """client.billing — read-only billing summary and upgrade requests."""

    upgrade_requests: AsyncUpgradeRequests

    def __init__(self, client: AsyncAPIClient) -> None:
        super().__init__(client)
        self.upgrade_requests = AsyncUpgradeRequests(client)

    async def get(self, *, max_retries: int | None = None) -> BillingSummary:
        resp = await self._request("GET", _BILLING_PATH, max_retries=max_retries)
        return self._build(BillingSummary, resp)
