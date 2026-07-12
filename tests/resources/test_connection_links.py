from __future__ import annotations

import httpx
import pytest
import respx

from chronary import AsyncChronary, Chronary, ConnectionLink

BASE = "https://api.chronary.ai"
LINK = {"id": "csl_1", "calendar_id": "cal_1", "setup_url": "https://api.test/setup", "status": "awaiting_human", "expires_at": "2026-07-12T12:00:00Z"}


@respx.mock
def test_sync_connection_link_lifecycle() -> None:
    respx.post(f"{BASE}/v1/calendars/cal_1/connection-links").mock(return_value=httpx.Response(201, json=LINK))
    respx.get(f"{BASE}/v1/connection-links/csl_1").mock(return_value=httpx.Response(200, json=LINK))
    respx.delete(f"{BASE}/v1/connection-links/csl_1").mock(return_value=httpx.Response(204))
    with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
        link = client.connection_links.create("cal_1", capabilities=["availability"])
        assert isinstance(link, ConnectionLink)
        assert client.connection_links.get("csl_1").status == "awaiting_human"
        client.connection_links.cancel("csl_1")


@pytest.mark.asyncio
@respx.mock
async def test_async_connection_link_lifecycle() -> None:
    respx.post(f"{BASE}/v1/calendars/cal_1/connection-links").mock(return_value=httpx.Response(201, json=LINK))
    respx.get(f"{BASE}/v1/connection-links/csl_1").mock(return_value=httpx.Response(200, json=LINK))
    respx.delete(f"{BASE}/v1/connection-links/csl_1").mock(return_value=httpx.Response(204))
    async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
        assert (await client.connection_links.create("cal_1", capabilities=["availability"])).id == "csl_1"
        assert (await client.connection_links.get("csl_1")).calendar_id == "cal_1"
        await client.connection_links.cancel("csl_1")
