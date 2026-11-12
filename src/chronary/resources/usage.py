from __future__ import annotations

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ResourceUsage(ChronaryModel):
    """Usage count for a single resource type."""

    used: int
    limit: int | None = None


class HoldsUsage(ChronaryModel):
    """Temporal-hold lifecycle counters.

    Informational — not gated by any plan limit. ``created``, ``confirmed``
    and ``expired`` are monthly counters; ``expired`` covers all three
    end-of-hold paths: TTL expiry, manual release, and priority-bump.
    ``active`` is a live count of unexpired holds, not a monthly counter.
    """

    created: int
    confirmed: int
    expired: int
    active: int


class CrossCalendarQueriesUsage(ChronaryModel):
    """Availability requests that touched more than one calendar.

    Informational — gated separately by the ``cross_calendar_availability``
    capability, not by this counter.
    """

    used: int


class UsageResponse(ChronaryModel):
    """Current billing-period usage for the organization."""

    period_start: str
    period_end: str
    # First instant of the next UTC month, when monthly counters reset.
    resets_at: str
    # When this response was computed. API calls can lag by up to 30 seconds.
    generated_at: str
    plan: str
    agents: ResourceUsage
    calendars: ResourceUsage
    events: ResourceUsage
    # Active recurring series masters. Plan-capped: Free 5, Pro 250.
    recurring_events: ResourceUsage
    # Active public booking pages. Plan-capped: Free 1, Pro 25.
    booking_pages: ResourceUsage
    api_calls: ResourceUsage
    webhooks: ResourceUsage
    availability_queries: ResourceUsage
    ical_subscriptions: ResourceUsage
    proposals: ResourceUsage
    holds: HoldsUsage
    cross_calendar_queries: CrossCalendarQueriesUsage


class UsageHistoryMetrics(ChronaryModel):
    """Monthly counter totals for one UTC calendar month."""

    api_calls: int
    events: int
    webhook_deliveries: int
    availability_queries: int
    proposals: int
    holds_created: int
    holds_confirmed: int
    holds_expired: int
    cross_calendar_queries: int


class UsageHistoryMonth(ChronaryModel):
    """One UTC calendar month of usage history."""

    # ``YYYY-MM``.
    period: str
    period_start: str
    period_end: str
    # True only for the current, partial month (the last entry).
    is_current: bool
    metrics: UsageHistoryMetrics


class UsageHistoryLimits(ChronaryModel):
    """The current plan's limits for the limited monthly metrics (None = unlimited)."""

    api_calls: int | None = None
    events: int | None = None
    webhook_deliveries: int | None = None
    availability_queries: int | None = None
    proposals: int | None = None


class UsageHistoryResponse(ChronaryModel):
    """Monthly usage totals, oldest month first, ending with the current month."""

    plan: str
    months: int
    limits: UsageHistoryLimits
    data: list[UsageHistoryMonth]


# ---------------------------------------------------------------------------
# Sync resource
# ---------------------------------------------------------------------------

_USAGE_PATH = "/v1/usage"
_USAGE_HISTORY_PATH = "/v1/usage/history"


class Usage(SyncAPIResource):
    """client.usage — synchronous usage queries."""

    def get(self, *, max_retries: int | None = None) -> UsageResponse:
        resp = self._request("GET", _USAGE_PATH, max_retries=max_retries)
        return self._build(UsageResponse, resp)

    def history(
        self, months: int = 6, *, max_retries: int | None = None
    ) -> UsageHistoryResponse:
        """Monthly totals for the last 1-12 UTC calendar months (org keys only)."""
        params = {"months": months}
        resp = self._request(
            "GET", _USAGE_HISTORY_PATH, params=params, max_retries=max_retries
        )
        return self._build(UsageHistoryResponse, resp)


# ---------------------------------------------------------------------------
# Async resource
# ---------------------------------------------------------------------------


class AsyncUsage(AsyncAPIResource):
    """client.usage — asynchronous usage queries."""

    async def get(self, *, max_retries: int | None = None) -> UsageResponse:
        resp = await self._request("GET", _USAGE_PATH, max_retries=max_retries)
        return self._build(UsageResponse, resp)

    async def history(
        self, months: int = 6, *, max_retries: int | None = None
    ) -> UsageHistoryResponse:
        """Monthly totals for the last 1-12 UTC calendar months (org keys only)."""
        params = {"months": months}
        resp = await self._request(
            "GET", _USAGE_HISTORY_PATH, params=params, max_retries=max_retries
        )
        return self._build(UsageHistoryResponse, resp)
