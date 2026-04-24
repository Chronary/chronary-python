from __future__ import annotations

import httpx
import respx

from chronary import AsyncChronary, Chronary, CreatedScopedApiKey, ScopedApiKey

BASE = "https://api.chronary.ai"

CREATED_KEY_DATA = {
    "id": "key_1",
    "key": "chr_ak_live_SECRET",
    "mode": "live",
    "key_prefix": "chr_ak_live_ABCD1234",
    "agent_id": "agt_1",
    "label": "Customer A",
    "created_at": "2026-04-17T16:20:00Z",
}

LIST_KEY_DATA = {
    "id": "key_2",
    "mode": "test",
    "key_prefix": "chr_ak_test_DCBA4321",
    "agent_id": "agt_2",
    "label": None,
    "created_at": "2026-04-17T16:25:00Z",
}


class TestSyncKeys:
    @respx.mock
    def test_create(self) -> None:
        respx.post(f"{BASE}/v1/keys").mock(
            return_value=httpx.Response(201, json=CREATED_KEY_DATA)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            key = client.keys.create(
                agent_id="agt_1",
                mode="live",
                label="Customer A",
            )
            assert isinstance(key, CreatedScopedApiKey)
            assert key.id == "key_1"
            assert key.key == "chr_ak_live_SECRET"

    @respx.mock
    def test_list(self) -> None:
        respx.get(f"{BASE}/v1/keys").mock(
            return_value=httpx.Response(200, json={"keys": [LIST_KEY_DATA]})
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            keys = client.keys.list()
            assert len(keys) == 1
            assert isinstance(keys[0], ScopedApiKey)
            assert keys[0].agent_id == "agt_2"

    @respx.mock
    def test_delete(self) -> None:
        respx.delete(f"{BASE}/v1/keys/key_1").mock(return_value=httpx.Response(204))
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            result = client.keys.delete("key_1")
            assert result is None

    @respx.mock
    def test_create_request_id(self) -> None:
        respx.post(f"{BASE}/v1/keys").mock(
            return_value=httpx.Response(
                201,
                json=CREATED_KEY_DATA,
                headers={"X-Request-Id": "req_key_create_1"},
            )
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            key = client.keys.create(agent_id="agt_1", mode="live")
            assert key._request_id == "req_key_create_1"


class TestAsyncKeys:
    @respx.mock
    async def test_create(self) -> None:
        respx.post(f"{BASE}/v1/keys").mock(
            return_value=httpx.Response(201, json=CREATED_KEY_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            key = await client.keys.create(agent_id="agt_1", mode="live")
            assert isinstance(key, CreatedScopedApiKey)
            assert key.key == "chr_ak_live_SECRET"

    @respx.mock
    async def test_list(self) -> None:
        respx.get(f"{BASE}/v1/keys").mock(
            return_value=httpx.Response(200, json={"keys": [LIST_KEY_DATA]})
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            keys = await client.keys.list()
            assert len(keys) == 1
            assert isinstance(keys[0], ScopedApiKey)

    @respx.mock
    async def test_delete(self) -> None:
        respx.delete(f"{BASE}/v1/keys/key_1").mock(return_value=httpx.Response(204))
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            result = await client.keys.delete("key_1")
            assert result is None
