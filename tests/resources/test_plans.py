from __future__ import annotations

import httpx
import respx

from chronary import AsyncChronary, Chronary, Plan, PlansListResponse

BASE = "https://api.chronary.ai"

CATALOG_FIXTURE = {
    "plans": [
        {
            "id": "free",
            "name": "Free",
            "tagline": "For prototyping and small agents",
            "price": 0,
            "currency": "usd",
            "limits": {
                "agents": 5,
                "calendars": 10,
                "events": 5000,
                "api_calls": 50000,
                "webhook_deliveries": 10000,
                "availability_queries": 10000,
                "ical_subscriptions": 3,
                "proposals": 500,
                "webhook_endpoints": 3,
                "scoped_keys": 0,
            },
            "display_features": ["5 agents"],
            "recommended": False,
        },
        {
            "id": "pro",
            "name": "Pro",
            "tagline": "For production agent workflows",
            "price": 2900,
            "currency": "usd",
            "limits": {
                "agents": 500,
                "calendars": 1000,
                "events": 500000,
                "api_calls": 1000000,
                "webhook_deliveries": 1000000,
                "availability_queries": 1000000,
                "ical_subscriptions": 100,
                "proposals": None,
            },
            "display_features": ["500 agents"],
            "recommended": True,
        },
        {
            "id": "custom",
            "name": "Custom",
            "tagline": "Custom limits, dedicated SLA",
            "price": None,
            "currency": None,
            "limits": None,
            "display_features": ["Custom volume limits"],
            "recommended": False,
            "custom_pricing": True,
            "contact_url": "https://chronary.ai/contact",
        },
    ]
}


class TestSyncPlans:
    @respx.mock
    def test_list_returns_catalog(self) -> None:
        route = respx.get(f"{BASE}/v1/plans").mock(
            return_value=httpx.Response(200, json=CATALOG_FIXTURE)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.plans.list()
        assert isinstance(result, PlansListResponse)
        assert len(result.plans) == 3
        assert result.plans[1].id == "pro"
        assert result.plans[1].price == 2900
        assert result.plans[1].recommended is True
        assert isinstance(result.plans[0], Plan)
        # Guards the endpoint/key caps previously absent from PlanLimits.
        assert result.plans[0].limits is not None
        assert result.plans[0].limits.webhook_endpoints == 3
        assert result.plans[0].limits.scoped_keys == 0
        assert route.called

    @respx.mock
    def test_custom_tier_has_custom_pricing(self) -> None:
        respx.get(f"{BASE}/v1/plans").mock(
            return_value=httpx.Response(200, json=CATALOG_FIXTURE)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.plans.list()
        ent = next(p for p in result.plans if p.id == "custom")
        assert ent.custom_pricing is True
        assert ent.price is None
        assert ent.currency is None
        assert ent.limits is None
        assert ent.contact_url == "https://chronary.ai/contact"

    @respx.mock
    def test_list_works_without_api_key(self) -> None:
        # Public endpoint — no Authorization header required.
        route = respx.get(f"{BASE}/v1/plans").mock(
            return_value=httpx.Response(200, json=CATALOG_FIXTURE)
        )
        with Chronary(api_key=None, base_url=BASE) as client:
            result = client.plans.list()
        assert len(result.plans) == 3
        req = route.calls.last.request
        assert "authorization" not in {k.lower() for k in req.headers.keys()}


class TestAsyncPlans:
    @respx.mock
    async def test_list(self) -> None:
        respx.get(f"{BASE}/v1/plans").mock(
            return_value=httpx.Response(200, json=CATALOG_FIXTURE)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = await client.plans.list()
        assert len(result.plans) == 3
        assert result.plans[0].id == "free"
