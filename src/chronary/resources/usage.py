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

    Informational — not gated by any plan limit. The funnel identity
    ``created == confirmed + expired + active`` holds, where ``active`` is
    derived (not stored). Counts cover all three end-of-hold paths: TTL
    expiry, manual release, and priority-bump.
    """

    created: int
    confirmed: int
    expired: int


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


# ---------------------------------------------------------------------------
# Sync resource
# ---------------------------------------------------------------------------

_USAGE_PATH = "/v1/usage"


class Usage(SyncAPIResource):
    """client.usage — synchronous usage queries."""

    def get(self, *, max_retries: int | None = None) -> UsageResponse:
        resp = self._request("GET", _USAGE_PATH, max_retries=max_retries)
        return self._build(UsageResponse, resp)


# ---------------------------------------------------------------------------
# Async resource
# ---------------------------------------------------------------------------


class AsyncUsage(AsyncAPIResource):
    """client.usage — asynchronous usage queries."""

    async def get(self, *, max_retries: int | None = None) -> UsageResponse:
        resp = await self._request("GET", _USAGE_PATH, max_retries=max_retries)
        return self._build(UsageResponse, resp)
