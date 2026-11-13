from __future__ import annotations

import httpx
import respx

from chronary import (
    AsyncChronary,
    Chronary,
    ResourceUsage,
    ScopedKeysUsage,
    UsageHistoryResponse,
    UsageResponse,
)

BASE = "https://api.chronary.ai"

_ZERO_METRICS = {
    "api_calls": 0,
    "events": 0,
    "webhook_deliveries": 0,
    "availability_queries": 0,
    "proposals": 0,
    "holds_created": 0,
    "holds_confirmed": 0,
    "holds_expired": 0,
    "cross_calendar_queries": 0,
}

HISTORY_DATA = {
    "plan": "free",
    "months": 2,
    "limits": {
        "api_calls": 1000,
        "events": 100,
        "webhook_deliveries": 1000,
        "availability_queries": 100,
        "proposals": None,
    },
    "data": [
        {
            "period": "2026-09",
            "period_start": "2026-09-01T00:00:00.000Z",
            "period_end": "2026-09-30T23:59:59.000Z",
            "is_current": False,
            "metrics": {**_ZERO_METRICS, "api_calls": 41220, "events": 3},
        },
        {
            "period": "2026-10",
            "period_start": "2026-10-01T00:00:00.000Z",
            "period_end": "2026-10-31T23:59:59.000Z",
            "is_current": True,
            "metrics": dict(_ZERO_METRICS),
        },
    ],
}

USAGE_DATA = {
    "period_start": "2026-04-01T00:00:00Z",
    "period_end": "2026-04-30T23:59:59Z",
    "resets_at": "2026-05-01T00:00:00.000Z",
    "generated_at": "2026-04-25T12:04:07.000Z",
    "plan": "free",
    "agents": {"used": 1, "limit": 1},
    "calendars": {"used": 1, "limit": 1},
    "events": {"used": 50, "limit": 100},
    "recurring_events": {"used": 1, "limit": 1},
    "booking_pages": {"used": 1, "limit": 1},
    "api_calls": {"used": 900, "limit": 1000},
    "webhooks": {"used": 50, "limit": 1000},
    "webhook_endpoints": {"used": 1, "limit": 1},
    "availability_queries": {"used": 30, "limit": 100},
    "ical_subscriptions": {"used": 0, "limit": 0},
    "proposals": {"used": 0, "limit": 0},
    "scoped_keys": {"count": 0, "limit": 0},
    "holds": {"created": 24, "confirmed": 18, "expired": 4, "active": 2},
    "cross_calendar_queries": {"used": 11},
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
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            usage = client.usage.get()
            assert isinstance(usage, UsageResponse)
            assert usage.plan == "free"
            assert usage.period_start == "2026-04-01T00:00:00Z"
            assert isinstance(usage.agents, ResourceUsage)
            assert usage.agents.used == 1
            assert usage.agents.limit == 1
            assert usage.events.used == 50
            assert isinstance(usage.recurring_events, ResourceUsage)
            assert usage.recurring_events.used == 1
            assert usage.recurring_events.limit == 1
            assert isinstance(usage.booking_pages, ResourceUsage)
            assert usage.booking_pages.used == 1
            assert usage.booking_pages.limit == 1
            assert usage.ical_subscriptions.used == 0
            assert usage.proposals.used == 0
            assert usage.proposals.limit == 0
            assert usage.holds.created == 24
            assert usage.holds.confirmed == 18
            assert usage.holds.expired == 4
            assert usage.holds.active == 2
            assert usage.resets_at == "2026-05-01T00:00:00.000Z"
            assert usage.generated_at == "2026-04-25T12:04:07.000Z"
            assert usage.cross_calendar_queries.used == 11
            assert isinstance(usage.webhook_endpoints, ResourceUsage)
            assert usage.webhook_endpoints.used == 1
            assert usage.webhook_endpoints.limit == 1
            assert isinstance(usage.scoped_keys, ScopedKeysUsage)
            assert usage.scoped_keys.count == 0
            assert usage.scoped_keys.limit == 0

    @respx.mock
    def test_request_id(self) -> None:
        respx.get(f"{BASE}/v1/usage").mock(
            return_value=httpx.Response(
                200, json=USAGE_DATA, headers={"X-Request-Id": "req_usage_1"}
            )
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            usage = client.usage.get()
            assert usage._request_id == "req_usage_1"

    @respx.mock
    def test_null_limit_on_scale_plan(self) -> None:
        data = {
            **USAGE_DATA,
            "plan": "scale",
            "agents": {"used": 100, "limit": None},
            "webhook_endpoints": {"used": 12, "limit": None},
            "scoped_keys": {"count": 40, "limit": None},
        }
        respx.get(f"{BASE}/v1/usage").mock(
            return_value=httpx.Response(200, json=data)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            usage = client.usage.get()
            assert usage.agents.limit is None
            assert usage.webhook_endpoints.limit is None
            assert usage.scoped_keys.count == 40
            assert usage.scoped_keys.limit is None

    @respx.mock
    def test_history(self) -> None:
        route = respx.get(f"{BASE}/v1/usage/history").mock(
            return_value=httpx.Response(200, json=HISTORY_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            history = client.usage.history(months=2)
            assert isinstance(history, UsageHistoryResponse)
            assert route.calls[0].request.url.params["months"] == "2"
            assert history.plan == "free"
            assert history.limits.api_calls == 1000
            assert history.limits.proposals is None
            assert [m.period for m in history.data] == ["2026-09", "2026-10"]
            assert history.data[-1].is_current is True
            assert history.data[0].metrics.api_calls == 41220

    @respx.mock
    def test_history_defaults_to_six_months(self) -> None:
        route = respx.get(f"{BASE}/v1/usage/history").mock(
            return_value=httpx.Response(200, json=HISTORY_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            client.usage.history()
            assert route.calls[0].request.url.params["months"] == "6"


# ---------------------------------------------------------------------------
# Async tests
# ---------------------------------------------------------------------------


class TestAsyncUsage:
    @respx.mock
    async def test_get(self) -> None:
        respx.get(f"{BASE}/v1/usage").mock(
            return_value=httpx.Response(200, json=USAGE_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            usage = await client.usage.get()
            assert isinstance(usage, UsageResponse)
            assert usage.plan == "free"
            assert usage.agents.used == 1
            assert usage.holds.created == 24
            assert usage.cross_calendar_queries.used == 11
            assert usage.webhook_endpoints.used == 1
            assert usage.scoped_keys.count == 0

    @respx.mock
    async def test_request_id(self) -> None:
        respx.get(f"{BASE}/v1/usage").mock(
            return_value=httpx.Response(
                200, json=USAGE_DATA, headers={"X-Request-Id": "req_async_usage"}
            )
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            usage = await client.usage.get()
            assert usage._request_id == "req_async_usage"

    @respx.mock
    async def test_history(self) -> None:
        route = respx.get(f"{BASE}/v1/usage/history").mock(
            return_value=httpx.Response(200, json=HISTORY_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            history = await client.usage.history(months=2)
            assert isinstance(history, UsageHistoryResponse)
            assert route.calls[0].request.url.params["months"] == "2"
            assert history.data[0].metrics.events == 3
