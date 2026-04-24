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


class UsageResponse(ChronaryModel):
    """Current billing-period usage for the organization."""

    period_start: str
    period_end: str
    plan: str
    agents: ResourceUsage
    calendars: ResourceUsage
    events: ResourceUsage
    api_calls: ResourceUsage
    webhooks: ResourceUsage
    availability_queries: ResourceUsage
    ical_subscriptions: ResourceUsage


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
