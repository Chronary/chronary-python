from __future__ import annotations

import httpx
import pytest
import respx

from chronary import (
    AgentSignUpResponse,
    AgentVerifyResponse,
    AsyncChronary,
    BadRequestError,
    Chronary,
    ChronaryError,
)

BASE = "https://api.chronary.ai"

NEW_ORG_RESPONSE = {
    "org_id": "org_abc123",
    "agent_id": "agt_abc123",
    "api_key": "chr_sk_restricted_abc",
    "message": "Verification code sent to email",
}

EXISTING_ORG_RESPONSE = {"message": "Verification code sent to email"}


class TestSyncAgentAuth:
    @respx.mock
    def test_sign_up_new_org_returns_credentials(self) -> None:
        route = respx.post(f"{BASE}/v1/agent/sign-up").mock(
            return_value=httpx.Response(200, json=NEW_ORG_RESPONSE)
        )
        # Public endpoint — construct without an api key.
        with Chronary(api_key=None, base_url=BASE) as client:
            result = client.agent_auth.sign_up(
                email="alice@example.com",
                agent_name="Alice Bot",
                tos_version="2026-04-17",
            )

        assert isinstance(result, AgentSignUpResponse)
        assert result.is_new_org is True
        assert result.api_key == "chr_sk_restricted_abc"
        assert result.org_id == "org_abc123"
        assert route.called

        req = route.calls.last.request
        # No Authorization header on the unauthenticated client.
        assert "authorization" not in {k.lower() for k in req.headers.keys()}
        sent = req.content.decode()
        assert "alice@example.com" in sent
        assert "2026-04-17" in sent

    @respx.mock
    def test_sign_up_existing_org_dedup_returns_only_message(self) -> None:
        respx.post(f"{BASE}/v1/agent/sign-up").mock(
            return_value=httpx.Response(200, json=EXISTING_ORG_RESPONSE)
        )
        with Chronary(api_key=None, base_url=BASE) as client:
            result = client.agent_auth.sign_up(
                email="alice@example.com",
                agent_name="Alice Bot",
                tos_version="2026-04-17",
            )

        assert result.is_new_org is False
        assert result.api_key is None
        assert result.org_id is None
        assert result.message == "Verification code sent to email"

    @respx.mock
    def test_sign_up_propagates_409_tos_version_stale(self) -> None:
        respx.post(f"{BASE}/v1/agent/sign-up").mock(
            return_value=httpx.Response(
                409,
                json={
                    "error": {
                        "type": "tos_version_stale",
                        "message": "The submitted terms-of-service version is out of date",
                        "current_version": "2026-05-01",
                        "request_id": "req_test1",
                    }
                },
            )
        )
        with Chronary(api_key=None, base_url=BASE, max_retries=0) as client:
            with pytest.raises(ChronaryError, match="out of date"):
                client.agent_auth.sign_up(
                    email="alice@example.com",
                    agent_name="Alice Bot",
                    tos_version="2026-01-01",
                )

    @respx.mock
    def test_verify_with_restricted_key_unlocks_full_access(self) -> None:
        route = respx.post(f"{BASE}/v1/agent/verify").mock(
            return_value=httpx.Response(
                200, json={"verified": True, "message": "Full access unlocked"}
            )
        )
        with Chronary(api_key="chr_sk_restricted_abc", base_url=BASE) as client:
            result = client.agent_auth.verify(otp="123456")

        assert isinstance(result, AgentVerifyResponse)
        assert result.verified is True
        assert result.message == "Full access unlocked"
        assert route.called

        req = route.calls.last.request
        assert req.headers["Authorization"] == "Bearer chr_sk_restricted_abc"
        sent = req.content.decode()
        assert "123456" in sent

    @respx.mock
    def test_verify_400_bad_otp_raises_bad_request_error(self) -> None:
        respx.post(f"{BASE}/v1/agent/verify").mock(
            return_value=httpx.Response(
                400,
                json={
                    "error": {
                        "type": "validation_error",
                        "message": "Invalid or expired verification code",
                        "request_id": "req_test1",
                    }
                },
            )
        )
        with Chronary(
            api_key="chr_sk_restricted_abc", base_url=BASE, max_retries=0
        ) as client:
            with pytest.raises(BadRequestError, match="Invalid or expired"):
                client.agent_auth.verify(otp="000000")


class TestAsyncAgentAuth:
    @respx.mock
    async def test_sign_up_new_org(self) -> None:
        respx.post(f"{BASE}/v1/agent/sign-up").mock(
            return_value=httpx.Response(200, json=NEW_ORG_RESPONSE)
        )
        async with AsyncChronary(api_key=None, base_url=BASE) as client:
            result = await client.agent_auth.sign_up(
                email="alice@example.com",
                agent_name="Alice Bot",
                tos_version="2026-04-17",
            )
        assert result.is_new_org is True
        assert result.api_key == "chr_sk_restricted_abc"

    @respx.mock
    async def test_verify(self) -> None:
        respx.post(f"{BASE}/v1/agent/verify").mock(
            return_value=httpx.Response(
                200, json={"verified": True, "message": "Full access unlocked"}
            )
        )
        async with AsyncChronary(
            api_key="chr_sk_restricted_abc", base_url=BASE
        ) as client:
            result = await client.agent_auth.verify(otp="123456")
        assert result.verified is True
