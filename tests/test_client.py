from __future__ import annotations

import os
import re
from unittest.mock import patch

import httpx
import pytest
import respx

from chronary import AsyncChronary, Chronary

_EMPTY_LIST = {"data": [], "total": 0, "limit": 20, "offset": 0}


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

    # #2520: a caller-supplied httpx client must still get the SDK's auth
    # headers and, when it has no base_url of its own, the SDK's base_url.
    @respx.mock
    def test_custom_client_with_base_url_sends_auth_and_user_agent(self) -> None:
        route = respx.get("https://api.chronary.ai/v1/agents").mock(
            return_value=httpx.Response(200, json=_EMPTY_LIST)
        )
        client = Chronary(
            api_key="chr_sk_x", httpx_client=httpx.Client(base_url="https://api.chronary.ai")
        )
        client.agents.list()
        req = route.calls.last.request
        assert req.headers.get("authorization") == "Bearer chr_sk_x"
        assert req.headers.get("user-agent", "").startswith("chronary-py/")

    @respx.mock
    def test_custom_client_readme_example_without_base_url(self) -> None:
        route = respx.get("https://api.chronary.ai/v1/agents").mock(
            return_value=httpx.Response(200, json=_EMPTY_LIST)
        )
        http_client = httpx.Client(transport=httpx.HTTPTransport(retries=3))
        client = Chronary(api_key="chr_sk_x", httpx_client=http_client)
        client.agents.list()
        assert route.calls.last.request.headers.get("authorization") == "Bearer chr_sk_x"

    @respx.mock
    def test_custom_client_without_base_url_uses_sdk_base_url(self) -> None:
        route = respx.get("https://dev.example.test/v1/agents").mock(
            return_value=httpx.Response(200, json=_EMPTY_LIST)
        )
        client = Chronary(
            api_key="chr_sk_x", base_url="https://dev.example.test/", httpx_client=httpx.Client()
        )
        client.agents.list()
        assert route.called

    @respx.mock
    def test_custom_client_without_key_sends_no_authorization(self) -> None:
        route = respx.get("https://api.chronary.ai/v1/plans").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        with patch.dict(os.environ, {}, clear=True):
            client = Chronary(httpx_client=httpx.Client())
        client._request("GET", "/v1/plans")
        assert "authorization" not in route.calls.last.request.headers

    @respx.mock
    def test_custom_client_own_headers_are_kept(self) -> None:
        # Review of #2520: the SDK must not override headers the caller set.
        route = respx.get("https://api.chronary.ai/v1/agents").mock(
            return_value=httpx.Response(200, json=_EMPTY_LIST)
        )
        http_client = httpx.Client(
            headers={"authorization": "Bearer from_client", "User-Agent": "my-app/1.0"}
        )
        client = Chronary(api_key="chr_sk_x", httpx_client=http_client)
        client.agents.list()
        req = route.calls.last.request
        assert req.headers.get("authorization") == "Bearer from_client"
        assert req.headers.get("user-agent") == "my-app/1.0"
        assert req.headers.get("accept") == "application/json"

    @respx.mock
    def test_custom_client_explicit_timeout_applies_per_request(self) -> None:
        route = respx.get("https://api.chronary.ai/v1/agents").mock(
            return_value=httpx.Response(200, json=_EMPTY_LIST)
        )
        client = Chronary(api_key="chr_sk_x", timeout=12.0, httpx_client=httpx.Client(timeout=5.0))
        client.agents.list()
        assert route.calls.last.request.extensions["timeout"]["read"] == 12.0

    @respx.mock
    def test_custom_client_keeps_its_own_timeout_when_none_passed(self) -> None:
        route = respx.get("https://api.chronary.ai/v1/agents").mock(
            return_value=httpx.Response(200, json=_EMPTY_LIST)
        )
        client = Chronary(api_key="chr_sk_x", httpx_client=httpx.Client(timeout=5.0))
        client.agents.list()
        assert route.calls.last.request.extensions["timeout"]["read"] == 5.0

    def test_default_timeout_is_60_seconds(self) -> None:
        client = Chronary(api_key="chr_sk_x")
        assert client._client.timeout.read == 60.0
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

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_custom_client_sends_auth(self) -> None:
        # #2520, async counterpart.
        route = respx.get("https://api.chronary.ai/v1/agents").mock(
            return_value=httpx.Response(200, json=_EMPTY_LIST)
        )
        client = AsyncChronary(
            api_key="chr_sk_x", httpx_client=httpx.AsyncClient(base_url="https://api.chronary.ai")
        )
        await client.agents.list()
        req = route.calls.last.request
        assert req.headers.get("authorization") == "Bearer chr_sk_x"
        assert req.headers.get("user-agent", "").startswith("chronary-py/")

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_custom_client_without_base_url(self) -> None:
        route = respx.get("https://api.chronary.ai/v1/agents").mock(
            return_value=httpx.Response(200, json=_EMPTY_LIST)
        )
        client = AsyncChronary(api_key="chr_sk_x", httpx_client=httpx.AsyncClient())
        await client.agents.list()
        assert route.calls.last.request.headers.get("authorization") == "Bearer chr_sk_x"

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_custom_client_own_authorization_is_kept(self) -> None:
        route = respx.get("https://api.chronary.ai/v1/agents").mock(
            return_value=httpx.Response(200, json=_EMPTY_LIST)
        )
        http_client = httpx.AsyncClient(headers={"Authorization": "Bearer from_client"})
        client = AsyncChronary(api_key="chr_sk_x", httpx_client=http_client)
        await client.agents.list()
        req = route.calls.last.request
        assert req.headers.get("authorization") == "Bearer from_client"
        assert req.headers.get("user-agent", "").startswith("chronary-py/")

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_custom_client_timeout(self) -> None:
        route = respx.get("https://api.chronary.ai/v1/agents").mock(
            return_value=httpx.Response(200, json=_EMPTY_LIST)
        )
        explicit = AsyncChronary(
            api_key="chr_sk_x", timeout=12.0, httpx_client=httpx.AsyncClient(timeout=5.0)
        )
        await explicit.agents.list()
        assert route.calls.last.request.extensions["timeout"]["read"] == 12.0
        implicit = AsyncChronary(api_key="chr_sk_x", httpx_client=httpx.AsyncClient(timeout=5.0))
        await implicit.agents.list()
        assert route.calls.last.request.extensions["timeout"]["read"] == 5.0

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
