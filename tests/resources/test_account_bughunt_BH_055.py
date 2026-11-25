"""bughunt-BH-055 (#2556): account.export() must return the parsed DataExport dict."""

from __future__ import annotations

import httpx
import pytest
import respx

from chronary import AsyncChronary, Chronary

BASE = "https://api.chronary.ai"
PAYLOAD = {"exported_at": "2026-11-20T00:00:00Z", "agents": []}


class TestAccountExportSync:
    @respx.mock
    def test_export_returns_dict(self) -> None:
        respx.get(f"{BASE}/v1/auth/export").mock(return_value=httpx.Response(200, json=PAYLOAD))
        with Chronary(api_key="jwt.token.value", base_url=BASE) as client:
            result = client.account.export()
        assert isinstance(result, dict), f"got {type(result)!r}"
        assert result["agents"] == []


class TestAccountExportAsync:
    @respx.mock
    @pytest.mark.asyncio
    async def test_export_returns_dict(self) -> None:
        respx.get(f"{BASE}/v1/auth/export").mock(return_value=httpx.Response(200, json=PAYLOAD))
        async with AsyncChronary(api_key="jwt.token.value", base_url=BASE) as client:
            result = await client.account.export()
        assert isinstance(result, dict), f"got {type(result)!r}"
        assert result["agents"] == []
