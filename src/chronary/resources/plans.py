from __future__ import annotations

from typing import Literal

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


PlanId = Literal["free", "pro", "scale", "enterprise"]


class PlanLimits(ChronaryModel):
    """Machine-readable monthly/total caps. `None` fields are unlimited."""

    agents: int | None = None
    calendars: int | None = None
    events: int | None = None
    api_calls: int | None = None
    webhook_deliveries: int | None = None
    availability_queries: int | None = None
    ical_subscriptions: int | None = None
    proposals: int | None = None


class Plan(ChronaryModel):
    """One tier in the public plan catalog."""

    id: PlanId
    name: str
    tagline: str
    price: int | None = None
    """Recurring monthly amount in the smallest currency unit (USD cents).
    `None` for custom-priced tiers."""
    currency: str | None = None
    """Lowercase ISO-4217 code. `None` for custom-priced tiers."""
    limits: PlanLimits | None = None
    """Enforced caps. `None` for custom-priced tiers."""
    display_features: list[str]
    """Marketing copy — use `limits` for capability checks."""
    recommended: bool
    """Hint for UIs to highlight a tier (currently `pro`)."""
    custom_pricing: bool | None = None
    """Present and `True` for the enterprise tier."""
    contact_url: str | None = None
    """Sales contact URL for custom-priced tiers."""


class PlansListResponse(ChronaryModel):
    """Response shape for GET /v1/plans."""

    plans: list[Plan]


# ---------------------------------------------------------------------------
# Sync / Async resources
# ---------------------------------------------------------------------------

_PLANS_PATH = "/v1/plans"


class Plans(SyncAPIResource):
    """client.plans — synchronous plan catalog queries."""

    def list(self, *, max_retries: int | None = None) -> PlansListResponse:
        resp = self._request("GET", _PLANS_PATH, max_retries=max_retries)
        return self._build(PlansListResponse, resp)


class AsyncPlans(AsyncAPIResource):
    """client.plans — asynchronous plan catalog queries."""

    async def list(self, *, max_retries: int | None = None) -> PlansListResponse:
        resp = await self._request("GET", _PLANS_PATH, max_retries=max_retries)
        return self._build(PlansListResponse, resp)
