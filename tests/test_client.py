from __future__ import annotations

import os
import re
from unittest.mock import patch

import httpx
import pytest
import respx

from chronary import AsyncChronary, Chronary


class TestSyncClient:
    def test_construct_with_explicit_key(self) -> None:
        client = Chronary(api_key="chr_sk_abc123")
        assert client._api_key == "chr_sk_abc123"
        client.close()

    def test_construct_from_env_var(self) -> None:
        with patch.dict(os.environ, {"CHRONARY_API_KEY": "chr_sk_env"}):
            client = Chronary()
            assert client._api_key == "chr_sk_env"
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
        client = Chronary(api_key="chr_sk_x")
        assert client.base_url == "https://api.chronary.ai"
        client.close()

    def test_default_timeout(self) -> None:
        client = Chronary(api_key="chr_sk_x")
        assert client._client.timeout.connect == 60.0
        client.close()

    def test_default_max_retries(self) -> None:
        client = Chronary(api_key="chr_sk_x")
        assert client.max_retries == 2
        client.close()

    def test_custom_httpx_client(self) -> None:
        custom = httpx.Client(base_url="https://custom.test")
        client = Chronary(api_key="chr_sk_x", httpx_client=custom)
        assert client._client is custom
        assert not client._owns_client
        client.close()

    def test_context_manager(self) -> None:
        with Chronary(api_key="chr_sk_x") as client:
            assert isinstance(client, Chronary)
        assert client._client.is_closed

    def test_agents_property(self) -> None:
        client = Chronary(api_key="chr_sk_x")
        agents = client.agents
        assert agents is client.agents  # same instance
        client.close()

    @respx.mock
    def test_user_agent_is_chronary_py(self) -> None:
        # The API attributes traffic by the leading chronary-* token in UA;
        # the Python SDK must identify as `chronary-py/<version>` so the
        # Better Stack SDK breakdown widget tags it correctly.
        route = respx.get("https://api.test.chronary.ai/v1/plans").mock(
            return_value=httpx.Response(200, json={"plans": []})
        )
        with Chronary(api_key="chr_sk_x", base_url="https://api.test.chronary.ai") as client:
            client.plans.list()
        ua = route.calls.last.request.headers.get("User-Agent", "")
        assert re.match(r"^chronary-py/\d+\.\d+\.\d+", ua), ua


class TestAsyncClient:
    def test_construct_with_explicit_key(self) -> None:
        client = AsyncChronary(api_key="chr_sk_abc123")
        assert client._api_key == "chr_sk_abc123"

    def test_construct_from_env_var(self) -> None:
        with patch.dict(os.environ, {"CHRONARY_API_KEY": "chr_sk_env"}):
            client = AsyncChronary()
            assert client._api_key == "chr_sk_env"

    def test_missing_key_constructs_without_error(self) -> None:
        # Mirrors TestSyncClient.test_missing_key_constructs_without_error.
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CHRONARY_API_KEY", None)
            client = AsyncChronary()
            assert client._api_key is None

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        async with AsyncChronary(api_key="chr_sk_x") as client:
            assert isinstance(client, AsyncChronary)
        assert client._client.is_closed

    def test_agents_property(self) -> None:
        client = AsyncChronary(api_key="chr_sk_x")
        agents = client.agents
        assert agents is client.agents  # same instance


class TestAgentKeyKwarg:
    """Coverage for api_key / agent_key kwargs and the key_type property."""

    def test_backend_key_sets_key_type_backend(self) -> None:
        client = Chronary(api_key="chr_sk_abc")
        assert client.key_type == "backend"
        assert client._api_key == "chr_sk_abc"
        client.close()

    def test_agent_key_sets_key_type_agent(self) -> None:
        client = Chronary(agent_key="chr_ak_abc")
        assert client.key_type == "agent"
        assert client._api_key == "chr_ak_abc"
        client.close()

    def test_agent_key_async_variant(self) -> None:
        client = AsyncChronary(agent_key="chr_ak_abc")
        assert client.key_type == "agent"
        assert client._api_key == "chr_ak_abc"

    def test_both_kwargs_explicit_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="not both"):
            Chronary(api_key="chr_sk_x", agent_key="chr_ak_y")

    def test_both_kwargs_explicit_raises_async_too(self) -> None:
        with pytest.raises(TypeError, match="not both"):
            AsyncChronary(api_key="chr_sk_x", agent_key="chr_ak_y")

    def test_neither_kwarg_neither_env_returns_none_key_type(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CHRONARY_API_KEY", None)
            os.environ.pop("CHRONARY_AGENT_KEY", None)
            client = Chronary()
            assert client.key_type is None
            assert client._api_key is None
            client.close()

    def test_agent_key_env_var_resolves(self) -> None:
        with patch.dict(os.environ, {"CHRONARY_AGENT_KEY": "chr_ak_env"}, clear=True):
            client = Chronary()
            assert client.key_type == "agent"
            assert client._api_key == "chr_ak_env"
            client.close()

    def test_both_env_vars_set_backend_wins(self) -> None:
        """Deterministic tiebreak when both env vars set — backend wins."""
        with patch.dict(
            os.environ,
            {"CHRONARY_API_KEY": "chr_sk_env", "CHRONARY_AGENT_KEY": "chr_ak_env"},
            clear=True,
        ):
            client = Chronary()
            assert client.key_type == "backend"
            assert client._api_key == "chr_sk_env"
            client.close()

    def test_explicit_api_key_overrides_agent_env(self) -> None:
        """Explicit kwarg beats an env var of the other kind."""
        with patch.dict(os.environ, {"CHRONARY_AGENT_KEY": "chr_ak_env"}, clear=True):
            client = Chronary(api_key="chr_sk_explicit")
            assert client.key_type == "backend"
            assert client._api_key == "chr_sk_explicit"
            client.close()
