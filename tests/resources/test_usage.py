from __future__ import annotations

import httpx
import respx

from chronary import AsyncChronary, Chronary, ResourceUsage, UsageResponse

BASE = "https://api.chronary.ai"

USAGE_DATA = {
    "period_start": "2026-04-01T00:00:00Z",
    "period_end": "2026-04-30T23:59:59Z",
    "plan": "free",
    "agents": {"used": 3, "limit": 5},
    "calendars": {"used": 5, "limit": 10},
    "events": {"used": 150, "limit": 5000},
    "api_calls": {"used": 1200, "limit": 50000},
    "webhooks": {"used": 50, "limit": 10000},
    "availability_queries": {"used": 30, "limit": 10000},
    "ical_subscriptions": {"used": 1, "limit": 3},
    "proposals": {"used": 18, "limit": 500},
}


# ---------------------------------------------------------------------------
# Sync tests
# ---------------------------------------------------------------------------


class TestSyncUsage:
    @respx.mock
    def test_get(self) -> None:
        respx.get(f"{BASE}/v1/usage").mock(
            return_value=httpx.Response(200, json=USAGE_DATA)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            usage = client.usage.get()
            assert isinstance(usage, UsageResponse)
            assert usage.plan == "free"
            assert usage.period_start == "2026-04-01T00:00:00Z"
            assert isinstance(usage.agents, ResourceUsage)
            assert usage.agents.used == 3
            assert usage.agents.limit == 5
            assert usage.events.used == 150
            assert usage.ical_subscriptions.used == 1
            assert usage.proposals.used == 18
            assert usage.proposals.limit == 500

    @respx.mock
    def test_request_id(self) -> None:
        respx.get(f"{BASE}/v1/usage").mock(
            return_value=httpx.Response(
                200, json=USAGE_DATA, headers={"X-Request-Id": "req_usage_1"}
            )
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            usage = client.usage.get()
            assert usage._request_id == "req_usage_1"

    @respx.mock
    def test_null_limit_on_scale_plan(self) -> None:
        data = {
            **USAGE_DATA,
            "plan": "scale",
            "agents": {"used": 100, "limit": None},
        }
        respx.get(f"{BASE}/v1/usage").mock(
            return_value=httpx.Response(200, json=data)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            usage = client.usage.get()
            assert usage.agents.limit is None


# ---------------------------------------------------------------------------
# Async tests
# ---------------------------------------------------------------------------


class TestAsyncUsage:
    @respx.mock
    async def test_get(self) -> None:
        respx.get(f"{BASE}/v1/usage").mock(
            return_value=httpx.Response(200, json=USAGE_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            usage = await client.usage.get()
            assert isinstance(usage, UsageResponse)
            assert usage.plan == "free"
            assert usage.agents.used == 3

    @respx.mock
    async def test_request_id(self) -> None:
        respx.get(f"{BASE}/v1/usage").mock(
            return_value=httpx.Response(
                200, json=USAGE_DATA, headers={"X-Request-Id": "req_async_usage"}
            )
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            usage = await client.usage.get()
            assert usage._request_id == "req_async_usage"
