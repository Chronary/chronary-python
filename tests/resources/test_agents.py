from __future__ import annotations

import httpx
import pytest
import respx

from chronary import Agent, AsyncChronary, Chronary
from chronary.pagination import AsyncPager, SyncPager

BASE = "https://api.chronary.ai"

AGENT_DATA = {
    "id": "agt_abc123",
    "name": "My Agent",
    "type": "ai",
    "description": "An AI agent",
    "status": "active",
    "metadata": {},
    "createdAt": "2026-01-15T10:30:00Z",
    "updatedAt": "2026-01-15T10:30:00Z",
}

LIST_RESPONSE = {
    "data": [AGENT_DATA],
    "total": 1,
    "limit": 50,
    "offset": 0,
}


# ---------------------------------------------------------------------------
# Sync tests
# ---------------------------------------------------------------------------


class TestSyncAgents:
    @respx.mock
    def test_create(self) -> None:
        respx.post(f"{BASE}/v1/agents").mock(
            return_value=httpx.Response(201, json=AGENT_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            agent = client.agents.create(name="My Agent", type="ai")
            assert isinstance(agent, Agent)
            assert agent.id == "agt_abc123"
            assert agent.name == "My Agent"

    @respx.mock
    def test_list(self) -> None:
        respx.get(f"{BASE}/v1/agents").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = client.agents.list()
            assert isinstance(pager, SyncPager)
            assert len(pager.data) == 1
            assert pager.total == 1
            assert not pager.has_more

    @respx.mock
    def test_get(self) -> None:
        respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            return_value=httpx.Response(200, json=AGENT_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            agent = client.agents.get("agt_abc123")
            assert agent.id == "agt_abc123"

    @respx.mock
    def test_update(self) -> None:
        updated = {**AGENT_DATA, "name": "Renamed"}
        respx.patch(f"{BASE}/v1/agents/agt_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            agent = client.agents.update("agt_abc123", name="Renamed")
            assert agent.name == "Renamed"

    @respx.mock
    def test_update_description_to_none(self) -> None:
        """Explicitly passing description=None should send null to clear it."""
        updated = {**AGENT_DATA, "description": None}
        route = respx.patch(f"{BASE}/v1/agents/agt_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            agent = client.agents.update("agt_abc123", description=None)
            assert agent.description is None
            # Verify the body included description: null
            sent_body = route.calls[0].request.content
            assert b'"description"' in sent_body

    @respx.mock
    def test_delete(self) -> None:
        respx.delete(f"{BASE}/v1/agents/agt_abc123").mock(
            return_value=httpx.Response(204)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.agents.delete("agt_abc123")
            assert result is None

    @respx.mock
    def test_create_request_id(self) -> None:
        respx.post(f"{BASE}/v1/agents").mock(
            return_value=httpx.Response(
                201, json=AGENT_DATA, headers={"X-Request-Id": "req_create_1"}
            )
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            agent = client.agents.create(name="My Agent", type="ai")
            assert agent._request_id == "req_create_1"

    @respx.mock
    def test_get_request_id(self) -> None:
        respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            return_value=httpx.Response(
                200, json=AGENT_DATA, headers={"X-Request-Id": "req_get_1"}
            )
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            agent = client.agents.get("agt_abc123")
            assert agent._request_id == "req_get_1"

    @respx.mock
    def test_update_request_id(self) -> None:
        updated = {**AGENT_DATA, "name": "Renamed"}
        respx.patch(f"{BASE}/v1/agents/agt_abc123").mock(
            return_value=httpx.Response(
                200, json=updated, headers={"X-Request-Id": "req_update_1"}
            )
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            agent = client.agents.update("agt_abc123", name="Renamed")
            assert agent._request_id == "req_update_1"

    @respx.mock
    def test_request_id_none_when_header_missing(self) -> None:
        respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            return_value=httpx.Response(200, json=AGENT_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            agent = client.agents.get("agt_abc123")
            assert agent._request_id is None

    @respx.mock
    def test_list_pager_request_id(self) -> None:
        respx.get(f"{BASE}/v1/agents").mock(
            return_value=httpx.Response(
                200, json=LIST_RESPONSE, headers={"X-Request-Id": "req_list_1"}
            )
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = client.agents.list()
            assert pager._request_id == "req_list_1"

    @respx.mock
    def test_auto_paging_iter_updates_request_id(self) -> None:
        page1 = {
            "data": [{**AGENT_DATA, "id": "agt_1"}],
            "total": 2,
            "limit": 1,
            "offset": 0,
        }
        page2 = {
            "data": [{**AGENT_DATA, "id": "agt_2"}],
            "total": 2,
            "limit": 1,
            "offset": 1,
        }
        respx.get(f"{BASE}/v1/agents").mock(
            side_effect=[
                httpx.Response(200, json=page1, headers={"X-Request-Id": "req_page1"}),
                httpx.Response(200, json=page2, headers={"X-Request-Id": "req_page2"}),
            ]
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = client.agents.list()
            assert pager._request_id == "req_page1"
            list(pager.auto_paging_iter())
            assert pager._request_id == "req_page2"

    @respx.mock
    def test_auto_paging_iter(self) -> None:
        page1 = {
            "data": [
                {**AGENT_DATA, "id": "agt_1"},
                {**AGENT_DATA, "id": "agt_2"},
            ],
            "total": 3,
            "limit": 2,
            "offset": 0,
        }
        page2 = {
            "data": [{**AGENT_DATA, "id": "agt_3"}],
            "total": 3,
            "limit": 2,
            "offset": 2,
        }
        respx.get(f"{BASE}/v1/agents").mock(
            side_effect=[
                httpx.Response(200, json=page1),
                httpx.Response(200, json=page2),
            ]
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = client.agents.list()
            all_agents = list(pager.auto_paging_iter())
            assert len(all_agents) == 3
            assert [a.id for a in all_agents] == ["agt_1", "agt_2", "agt_3"]


# ---------------------------------------------------------------------------
# Async tests
# ---------------------------------------------------------------------------


class TestAsyncAgents:
    @respx.mock
    @pytest.mark.asyncio
    async def test_create(self) -> None:
        respx.post(f"{BASE}/v1/agents").mock(
            return_value=httpx.Response(201, json=AGENT_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            agent = await client.agents.create(name="My Agent", type="ai")
            assert isinstance(agent, Agent)
            assert agent.id == "agt_abc123"

    @respx.mock
    @pytest.mark.asyncio
    async def test_list(self) -> None:
        respx.get(f"{BASE}/v1/agents").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = await client.agents.list()
            assert isinstance(pager, AsyncPager)
            assert len(pager.data) == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_get(self) -> None:
        respx.get(f"{BASE}/v1/agents/agt_abc123").mock(
            return_value=httpx.Response(200, json=AGENT_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            agent = await client.agents.get("agt_abc123")
            assert agent.id == "agt_abc123"

    @respx.mock
    @pytest.mark.asyncio
    async def test_update(self) -> None:
        updated = {**AGENT_DATA, "name": "Renamed"}
        respx.patch(f"{BASE}/v1/agents/agt_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            agent = await client.agents.update("agt_abc123", name="Renamed")
            assert agent.name == "Renamed"

    @respx.mock
    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        respx.delete(f"{BASE}/v1/agents/agt_abc123").mock(
            return_value=httpx.Response(204)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = await client.agents.delete("agt_abc123")
            assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_request_id(self) -> None:
        respx.post(f"{BASE}/v1/agents").mock(
            return_value=httpx.Response(
                201, json=AGENT_DATA, headers={"X-Request-Id": "req_async_create"}
            )
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            agent = await client.agents.create(name="My Agent", type="ai")
            assert agent._request_id == "req_async_create"

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_pager_request_id(self) -> None:
        respx.get(f"{BASE}/v1/agents").mock(
            return_value=httpx.Response(
                200, json=LIST_RESPONSE, headers={"X-Request-Id": "req_async_list"}
            )
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = await client.agents.list()
            assert pager._request_id == "req_async_list"

    @respx.mock
    @pytest.mark.asyncio
    async def test_auto_paging_iter_updates_request_id(self) -> None:
        page1 = {
            "data": [{**AGENT_DATA, "id": "agt_1"}],
            "total": 2,
            "limit": 1,
            "offset": 0,
        }
        page2 = {
            "data": [{**AGENT_DATA, "id": "agt_2"}],
            "total": 2,
            "limit": 1,
            "offset": 1,
        }
        respx.get(f"{BASE}/v1/agents").mock(
            side_effect=[
                httpx.Response(200, json=page1, headers={"X-Request-Id": "req_p1"}),
                httpx.Response(200, json=page2, headers={"X-Request-Id": "req_p2"}),
            ]
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = await client.agents.list()
            assert pager._request_id == "req_p1"
            [a async for a in pager.auto_paging_iter()]
            assert pager._request_id == "req_p2"

    @respx.mock
    @pytest.mark.asyncio
    async def test_auto_paging_iter(self) -> None:
        page1 = {
            "data": [
                {**AGENT_DATA, "id": "agt_1"},
                {**AGENT_DATA, "id": "agt_2"},
            ],
            "total": 3,
            "limit": 2,
            "offset": 0,
        }
        page2 = {
            "data": [{**AGENT_DATA, "id": "agt_3"}],
            "total": 3,
            "limit": 2,
            "offset": 2,
        }
        respx.get(f"{BASE}/v1/agents").mock(
            side_effect=[
                httpx.Response(200, json=page1),
                httpx.Response(200, json=page2),
            ]
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = await client.agents.list()
            all_agents = [a async for a in pager.auto_paging_iter()]
            assert len(all_agents) == 3
            assert [a.id for a in all_agents] == ["agt_1", "agt_2", "agt_3"]
