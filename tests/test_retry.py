from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
import respx

from chronary import AsyncChronary, Chronary, InternalServerError
from chronary._base_client import _sleep_time
from chronary._exceptions import APIConnectionError, APITimeoutError, QuotaExceededError

BASE = "https://api.chronary.ai"

AGENT_DATA = {
    "id": "agt_abc123",
    "name": "My Agent",
    "type": "ai",
    "description": None,
    "status": "active",
    "metadata": {},
    "createdAt": "2026-01-15T10:30:00Z",
    "updatedAt": "2026-01-15T10:30:00Z",
}


class TestSyncRetry:
    @respx.mock
    def test_retry_on_429_then_success(self) -> None:
        error_body = {
            "error": {"type": "rate_limit_error", "message": "Too many requests"}
        }
        respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            side_effect=[
                httpx.Response(429, json=error_body, headers={"Retry-After": "0"}),
                httpx.Response(200, json=AGENT_DATA),
            ]
        )
        with (
            Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=1) as client,
            patch("chronary._base_client.time.sleep"),
        ):
            agent = client.agents.get("agt_abc123")
            assert agent.id == "agt_abc123"

    @respx.mock
    def test_retry_on_500_then_success(self) -> None:
        error_body = {"error": {"type": "internal_error", "message": "Oops"}}
        respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            side_effect=[
                httpx.Response(500, json=error_body),
                httpx.Response(200, json=AGENT_DATA),
            ]
        )
        with (
            Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=1) as client,
            patch("chronary._base_client.time.sleep"),
        ):
            agent = client.agents.get("agt_abc123")
            assert agent.id == "agt_abc123"

    @respx.mock
    def test_respects_retry_after_header(self) -> None:
        error_body = {
            "error": {"type": "rate_limit_error", "message": "Too many requests"}
        }
        respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            side_effect=[
                httpx.Response(429, json=error_body, headers={"Retry-After": "2"}),
                httpx.Response(200, json=AGENT_DATA),
            ]
        )
        with (
            Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=1) as client,
            patch("chronary._base_client.time.sleep") as mock_sleep,
        ):
            client.agents.get("agt_abc123")
            mock_sleep.assert_called_once_with(2.0)

    @respx.mock
    def test_max_retries_exhausted(self) -> None:
        error_body = {"error": {"type": "internal_error", "message": "Down"}}
        respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            side_effect=[
                httpx.Response(500, json=error_body),
                httpx.Response(500, json=error_body),
                httpx.Response(500, json=error_body),
            ]
        )
        with (
            Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=2) as client,
            patch("chronary._base_client.time.sleep"),
            pytest.raises(InternalServerError),
        ):
            client.agents.get("agt_abc123")

    @respx.mock
    def test_per_request_max_retries(self) -> None:
        error_body = {"error": {"type": "internal_error", "message": "Down"}}
        respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            side_effect=[
                httpx.Response(500, json=error_body),
                httpx.Response(500, json=error_body),
            ]
        )
        with (
            Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=5) as client,
            patch("chronary._base_client.time.sleep"),
            pytest.raises(InternalServerError),
        ):
            client.agents.get("agt_abc123", max_retries=1)

    @respx.mock
    def test_timeout_handling(self) -> None:
        request = httpx.Request("GET", f"{BASE}/v1/agents/agt_abc123")
        respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            side_effect=httpx.ReadTimeout("Timed out", request=request)
        )
        with Chronary(
            api_key="chr_sk_x", base_url=BASE, max_retries=0
        ) as client, pytest.raises(APITimeoutError):
            client.agents.get("agt_abc123")


class TestAsyncRetry:
    @respx.mock
    @pytest.mark.asyncio
    async def test_retry_on_429_then_success(self) -> None:
        error_body = {
            "error": {"type": "rate_limit_error", "message": "Too many requests"}
        }
        respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            side_effect=[
                httpx.Response(429, json=error_body, headers={"Retry-After": "0"}),
                httpx.Response(200, json=AGENT_DATA),
            ]
        )
        async with AsyncChronary(
            api_key="chr_sk_x", base_url=BASE, max_retries=1
        ) as client:
            with patch("chronary._base_client._async_sleep"):
                agent = await client.agents.get("agt_abc123")
                assert agent.id == "agt_abc123"

    @respx.mock
    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self) -> None:
        error_body = {"error": {"type": "internal_error", "message": "Down"}}
        respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            side_effect=[
                httpx.Response(500, json=error_body),
                httpx.Response(500, json=error_body),
            ]
        )
        async with AsyncChronary(
            api_key="chr_sk_x", base_url=BASE, max_retries=1
        ) as client:
            with patch("chronary._base_client._async_sleep"):
                with pytest.raises(InternalServerError):
                    await client.agents.get("agt_abc123")

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_timeout(self) -> None:
        request = httpx.Request("GET", f"{BASE}/v1/agents/agt_abc123")
        respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            side_effect=httpx.ReadTimeout("Timed out", request=request)
        )
        async with AsyncChronary(
            api_key="chr_sk_x", base_url=BASE, max_retries=0
        ) as client:
            with pytest.raises(APITimeoutError):
                await client.agents.get("agt_abc123")

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_retry_on_500_then_success(self) -> None:
        error_body = {"error": {"type": "internal_error", "message": "Oops"}}
        respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            side_effect=[
                httpx.Response(500, json=error_body),
                httpx.Response(200, json=AGENT_DATA),
            ]
        )
        async with AsyncChronary(
            api_key="chr_sk_x", base_url=BASE, max_retries=1
        ) as client:
            with patch("chronary._base_client._async_sleep"):
                agent = await client.agents.get("agt_abc123")
                assert agent.id == "agt_abc123"

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_post_idempotency_header(self) -> None:
        error_body = {"error": {"type": "internal_error", "message": "Oops"}}
        route = respx.post(f"{BASE}/v1/agents").mock(
            side_effect=[
                httpx.Response(500, json=error_body),
                httpx.Response(201, json=AGENT_DATA),
            ]
        )
        async with AsyncChronary(
            api_key="chr_sk_x", base_url=BASE, max_retries=1
        ) as client:
            with patch("chronary._base_client._async_sleep"):
                await client.agents.create(name="My Agent", type="ai")
                first_req = route.calls[0].request
                retry_req = route.calls[1].request
                assert "Idempotency-Key" in first_req.headers
                assert retry_req.headers["Idempotency-Key"] == first_req.headers["Idempotency-Key"]


QUOTA_BODY = {
    "error": {
        "type": "quota_exceeded",
        "message": "Monthly API call limit of 1,000 reached.",
        "metric": "api_calls",
    }
}


class TestQuotaExceededIsNotRetried:
    """#1936: a monthly quota 429 raises at once; a rate-limit 429 still retries."""

    @respx.mock
    def test_quota_exceeded_raises_without_retry_or_sleep(self) -> None:
        route = respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            return_value=httpx.Response(429, json=QUOTA_BODY, headers={"Retry-After": "1700000"})
        )
        with (
            Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=2) as client,
            patch("chronary._base_client.time.sleep") as sleep,
            pytest.raises(QuotaExceededError),
        ):
            client.agents.get("agt_abc123")
        assert route.call_count == 1
        sleep.assert_not_called()

    @respx.mock
    def test_rate_limit_429_still_retries_with_retry_after(self) -> None:
        error_body = {"error": {"type": "rate_limit_error", "message": "Too many requests"}}
        route = respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            side_effect=[
                httpx.Response(429, json=error_body, headers={"Retry-After": "2"}),
                httpx.Response(200, json=AGENT_DATA),
            ]
        )
        with (
            Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=2) as client,
            patch("chronary._base_client.time.sleep") as sleep,
        ):
            agent = client.agents.get("agt_abc123")
        assert agent.id == "agt_abc123"
        assert route.call_count == 2
        sleep.assert_called_once_with(2.0)

    @respx.mock
    def test_long_rate_limit_retry_after_is_clamped(self) -> None:
        error_body = {"error": {"type": "rate_limit_error", "message": "Too many requests"}}
        respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            side_effect=[
                httpx.Response(429, json=error_body, headers={"Retry-After": "1700000"}),
                httpx.Response(200, json=AGENT_DATA),
            ]
        )
        with (
            Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=1) as client,
            patch("chronary._base_client.time.sleep") as sleep,
        ):
            client.agents.get("agt_abc123")
        sleep.assert_called_once_with(60.0)

    @pytest.mark.asyncio
    @respx.mock
    async def test_async_quota_exceeded_raises_without_retry_or_sleep(self) -> None:
        route = respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            return_value=httpx.Response(429, json=QUOTA_BODY, headers={"Retry-After": "1700000"})
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE, max_retries=2) as client:
            with (
                patch("chronary._base_client._async_sleep") as sleep,
                pytest.raises(QuotaExceededError),
            ):
                await client.agents.get("agt_abc123")
        assert route.call_count == 1
        sleep.assert_not_called()


class TestSleepTime:
    def test_respects_retry_after(self) -> None:
        assert _sleep_time(0, "2") == 2.0

    def test_caps_long_retry_after(self) -> None:
        # Monthly quota 429: Retry-After is seconds to the end of the month.
        assert _sleep_time(0, "1555200") == 60.0
        # Daily feedback cap: seconds to the next UTC midnight.
        assert _sleep_time(1, "6600") == 60.0

    def test_negative_retry_after_clamped_to_zero(self) -> None:
        assert _sleep_time(0, "-5") == 0.0

    def test_nan_retry_after_falls_back(self) -> None:
        result = _sleep_time(0, "nan")
        assert 0 < result <= 8.0 * 1.25

    def test_invalid_retry_after_falls_back(self) -> None:
        result = _sleep_time(0, "not-a-number")
        assert result > 0

    def test_backoff_increases(self) -> None:
        with patch("chronary._base_client.random.random", return_value=0):
            t0 = _sleep_time(0, None)
            t1 = _sleep_time(1, None)
            assert t1 > t0


class TestSyncIdempotency:
    @respx.mock
    def test_post_retry_includes_idempotency_key(self) -> None:
        error_body = {"error": {"type": "internal_error", "message": "Oops"}}
        route = respx.post(f"{BASE}/v1/agents").mock(
            side_effect=[
                httpx.Response(500, json=error_body),
                httpx.Response(201, json=AGENT_DATA),
            ]
        )
        with (
            Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=1) as client,
            patch("chronary._base_client.time.sleep"),
        ):
            client.agents.create(name="My Agent", type="ai")
            first_req = route.calls[0].request
            retry_req = route.calls[1].request
            assert "Idempotency-Key" in retry_req.headers
            assert retry_req.headers["Idempotency-Key"] == first_req.headers["Idempotency-Key"]

    @respx.mock
    def test_mutating_methods_send_idempotency_key_on_first_attempt(self) -> None:
        route = respx.patch(f"{BASE}/v1/agents/agt_abc123").mock(
            return_value=httpx.Response(200, json=AGENT_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client:
            client.agents.update("agt_abc123", name="Renamed")
            assert "Idempotency-Key" in route.calls[0].request.headers

    @respx.mock
    def test_low_level_idempotency_key_override(self) -> None:
        route = respx.post(f"{BASE}/v1/agents").mock(
            return_value=httpx.Response(201, json=AGENT_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client:
            client._request(
                "POST",
                "/v1/agents",
                json={"name": "My Agent", "type": "ai"},
                idempotency_key="idem_custom",
            )
            assert route.calls[0].request.headers["Idempotency-Key"] == "idem_custom"

    @respx.mock
    def test_connect_error_retry(self) -> None:
        request = httpx.Request("GET", f"{BASE}/v1/agents/agt_abc123")
        respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            side_effect=[
                httpx.ConnectError("Connection refused", request=request),
                httpx.Response(200, json=AGENT_DATA),
            ]
        )
        with (
            Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=1) as client,
            patch("chronary._base_client.time.sleep"),
        ):
            agent = client.agents.get("agt_abc123")
            assert agent.id == "agt_abc123"

    @respx.mock
    def test_connect_error_exhausted(self) -> None:
        request = httpx.Request("GET", f"{BASE}/v1/agents/agt_abc123")
        respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            side_effect=[
                httpx.ConnectError("Connection refused", request=request),
                httpx.ConnectError("Connection refused", request=request),
            ]
        )
        with (
            Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=1) as client,
            patch("chronary._base_client.time.sleep"),
            pytest.raises(APIConnectionError),
        ):
            client.agents.get("agt_abc123")
