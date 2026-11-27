from __future__ import annotations

import httpx
import pytest
import respx

from chronary import (
    AsyncChronary,
    AuthenticationError,
    BadRequestError,
    Chronary,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    QuotaExceededError,
    RateLimitError,
)
from chronary._exceptions import APIStatusError

BASE = "https://api.chronary.ai"


def _error_body(error_type: str, message: str, param: str | None = None) -> dict:
    body: dict = {
        "error": {
            "type": error_type,
            "message": message,
            "request_id": "req_abc123def456abcd",
        }
    }
    if param:
        body["error"]["param"] = param
    return body


class TestSyncExceptions:
    @respx.mock
    def test_400_bad_request(self) -> None:
        body = _error_body("validation_error", "Name is required", param="name")
        respx.get(f"{BASE}/v1/agents/agt_1").mock(
            return_value=httpx.Response(400, json=body)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client:
            with pytest.raises(BadRequestError) as exc_info:
                client.agents.get("agt_1")
            err = exc_info.value
            assert err.status_code == 400
            assert err.request_id == "req_abc123def456abcd"
            assert err.param == "name"
            assert err.error_type == "validation_error"

    @respx.mock
    def test_401_authentication(self) -> None:
        body = _error_body("authentication_error", "Invalid API key")
        respx.get(f"{BASE}/v1/agents/agt_1").mock(
            return_value=httpx.Response(401, json=body)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client:
            with pytest.raises(AuthenticationError) as exc_info:
                client.agents.get("agt_1")
            assert exc_info.value.status_code == 401
            assert exc_info.value.error_type == "authentication_error"

    @respx.mock
    def test_403_permission_denied(self) -> None:
        body = _error_body("forbidden", "Access denied")
        respx.get(f"{BASE}/v1/agents/agt_1").mock(
            return_value=httpx.Response(403, json=body)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client:
            with pytest.raises(PermissionDeniedError) as exc_info:
                client.agents.get("agt_1")
            assert exc_info.value.status_code == 403

    @respx.mock
    def test_404_not_found(self) -> None:
        body = _error_body("not_found", "Agent not found")
        respx.get(f"{BASE}/v1/agents/agt_1").mock(
            return_value=httpx.Response(404, json=body)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client:
            with pytest.raises(NotFoundError) as exc_info:
                client.agents.get("agt_1")
            assert exc_info.value.status_code == 404

    @respx.mock
    def test_429_rate_limit(self) -> None:
        body = _error_body("rate_limit_error", "Too many requests")
        respx.get(f"{BASE}/v1/agents/agt_1").mock(
            return_value=httpx.Response(429, json=body)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client:
            with pytest.raises(RateLimitError) as exc_info:
                client.agents.get("agt_1")
            assert exc_info.value.status_code == 429
            assert exc_info.value.error_type == "rate_limit_error"

    @respx.mock
    def test_429_quota_exceeded(self) -> None:
        body = _error_body("quota_exceeded", "Monthly quota exceeded")
        respx.get(f"{BASE}/v1/agents/agt_1").mock(
            return_value=httpx.Response(429, json=body)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client:
            with pytest.raises(QuotaExceededError) as exc_info:
                client.agents.get("agt_1")
            assert exc_info.value.status_code == 429
            assert exc_info.value.error_type == "quota_exceeded"
            assert not isinstance(exc_info.value, RateLimitError)

    @respx.mock
    def test_500_internal_server_error(self) -> None:
        body = _error_body("internal_error", "Internal server error")
        respx.get(f"{BASE}/v1/agents/agt_1").mock(
            return_value=httpx.Response(500, json=body)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client:
            with pytest.raises(InternalServerError) as exc_info:
                client.agents.get("agt_1")
            assert exc_info.value.status_code == 500

    @respx.mock
    def test_unknown_5xx_maps_to_internal(self) -> None:
        body = _error_body("internal_error", "Bad gateway")
        respx.get(f"{BASE}/v1/agents/agt_1").mock(
            return_value=httpx.Response(502, json=body)
        )
        with (
            Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client,
            pytest.raises(InternalServerError),
        ):
            client.agents.get("agt_1")

    @respx.mock
    def test_unknown_4xx_maps_to_api_status_error(self) -> None:
        body = _error_body("unknown_error", "Something weird")
        respx.get(f"{BASE}/v1/agents/agt_1").mock(
            return_value=httpx.Response(418, json=body)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client:
            with pytest.raises(APIStatusError) as exc_info:
                client.agents.get("agt_1")
            assert exc_info.value.status_code == 418
            assert exc_info.value.code is None
            assert exc_info.value.conflicting_event_ids == []

    @respx.mock
    def test_409_event_conflict_exposes_code_and_ids(self) -> None:
        body = _error_body("conflict", "This calendar refuses overlapping events")
        body["error"]["code"] = "event_conflict"
        body["error"]["conflicting_event_ids"] = ["evt_1", "evt_2"]
        respx.post(f"{BASE}/v1/calendars/cal_1/events").mock(
            return_value=httpx.Response(409, json=body)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client:
            with pytest.raises(APIStatusError) as exc_info:
                client.events.create(
                    "cal_1",
                    title="Call",
                    start_time="2026-12-01T10:00:00Z",
                    end_time="2026-12-01T11:00:00Z",
                )
            err = exc_info.value
            assert err.status_code == 409
            assert err.error_type == "conflict"
            assert err.code == "event_conflict"
            assert err.conflicting_event_ids == ["evt_1", "evt_2"]


class TestAsyncExceptions:
    @respx.mock
    @pytest.mark.asyncio
    async def test_400_bad_request(self) -> None:
        body = _error_body("validation_error", "Name is required", param="name")
        respx.get(f"{BASE}/v1/agents/agt_1").mock(
            return_value=httpx.Response(400, json=body)
        )
        async with AsyncChronary(
            api_key="chr_sk_x", base_url=BASE, max_retries=0
        ) as client:
            with pytest.raises(BadRequestError) as exc_info:
                await client.agents.get("agt_1")
            assert exc_info.value.param == "name"

    @respx.mock
    @pytest.mark.asyncio
    async def test_429_distinguishes_rate_limit_from_quota(self) -> None:
        rl_body = _error_body("rate_limit_error", "Too many requests")
        respx.get(f"{BASE}/v1/agents/agt_1").mock(
            return_value=httpx.Response(429, json=rl_body)
        )
        async with AsyncChronary(
            api_key="chr_sk_x", base_url=BASE, max_retries=0
        ) as client:
            with pytest.raises(RateLimitError):
                await client.agents.get("agt_1")
