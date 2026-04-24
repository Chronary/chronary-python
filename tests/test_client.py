from __future__ import annotations

import os
from unittest.mock import patch

import httpx
import pytest

from chronary import AsyncChronary, Chronary


class TestSyncClient:
    def test_construct_with_explicit_key(self) -> None:
        client = Chronary(api_key="chr_sk_test_abc123")
        assert client._api_key == "chr_sk_test_abc123"
        client.close()

    def test_construct_from_env_var(self) -> None:
        with patch.dict(os.environ, {"CHRONARY_API_KEY": "chr_sk_test_env"}):
            client = Chronary()
            assert client._api_key == "chr_sk_test_env"
            client.close()

    def test_missing_key_constructs_without_error(self) -> None:
        # Some endpoints (plans.list, agent_auth.sign_up) do not require auth,
        # so the SDK accepts construction without an api_key. Authed endpoints
        # surface 401 from the server at request time.
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CHRONARY_API_KEY", None)
            client = Chronary()
            assert client._api_key is None

    def test_default_base_url(self) -> None:
        client = Chronary(api_key="chr_sk_test_x")
        assert client.base_url == "https://api.chronary.ai"
        client.close()

    def test_default_timeout(self) -> None:
        client = Chronary(api_key="chr_sk_test_x")
        assert client._client.timeout.connect == 60.0
        client.close()

    def test_default_max_retries(self) -> None:
        client = Chronary(api_key="chr_sk_test_x")
        assert client.max_retries == 2
        client.close()

    def test_custom_httpx_client(self) -> None:
        custom = httpx.Client(base_url="https://custom.test")
        client = Chronary(api_key="chr_sk_test_x", httpx_client=custom)
        assert client._client is custom
        assert not client._owns_client
        client.close()

    def test_context_manager(self) -> None:
        with Chronary(api_key="chr_sk_test_x") as client:
            assert isinstance(client, Chronary)
        assert client._client.is_closed

    def test_agents_property(self) -> None:
        client = Chronary(api_key="chr_sk_test_x")
        agents = client.agents
        assert agents is client.agents  # same instance
        client.close()


class TestAsyncClient:
    def test_construct_with_explicit_key(self) -> None:
        client = AsyncChronary(api_key="chr_sk_test_abc123")
        assert client._api_key == "chr_sk_test_abc123"

    def test_construct_from_env_var(self) -> None:
        with patch.dict(os.environ, {"CHRONARY_API_KEY": "chr_sk_test_env"}):
            client = AsyncChronary()
            assert client._api_key == "chr_sk_test_env"

    def test_missing_key_constructs_without_error(self) -> None:
        # Mirrors TestSyncClient.test_missing_key_constructs_without_error.
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CHRONARY_API_KEY", None)
            client = AsyncChronary()
            assert client._api_key is None

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        async with AsyncChronary(api_key="chr_sk_test_x") as client:
            assert isinstance(client, AsyncChronary)
        assert client._client.is_closed

    def test_agents_property(self) -> None:
        client = AsyncChronary(api_key="chr_sk_test_x")
        agents = client.agents
        assert agents is client.agents  # same instance
