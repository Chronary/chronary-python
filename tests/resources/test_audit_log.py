from __future__ import annotations

import httpx
import respx

from chronary import AsyncChronary, Chronary
from chronary.resources.audit_log import AuditLogResponse

BASE = "https://api.chronary.ai"

PAGE = {
    "data": [
        {
            "id": "aud_1",
            "action": "agent_key.create",
            "actor_key_prefix": None,
            "actor_type": "session",
            "actor_id": "org_1",
            "actor_label": "owner@example.com",
            "agent_id": None,
            "resource": "",
            "ip": "203.0.113.7",
            "status": 201,
            "method": "POST",
            "path": "/v1/auth/keys/scoped",
            "duration_ms": 12,
            "request_id": "req_1",
            "created_at": "2026-10-30T00:00:00.000Z",
        }
    ],
    "pagination": {"next_cursor": None},
    "retention_days": 90,
    "range_clamped": False,
}

FILTERS = {
    "actor_type": "session",
    "actor_id": "org_1",
    "request_id": "req_1",
    "resource": "cal_",
    "status_class": "2xx",
    "category": "keys",
}


class TestSyncAuditLog:
    @respx.mock
    def test_list_sends_actor_filters(self) -> None:
        route = respx.get(f"{BASE}/v1/audit-log").mock(
            return_value=httpx.Response(200, json=PAGE)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            page = client.audit_log.list(action="agent_key.create", **FILTERS)
        assert isinstance(page, AuditLogResponse)
        entry = page.data[0]
        assert entry.actor_type == "session"
        assert entry.actor_id == "org_1"
        assert entry.actor_label == "owner@example.com"
        sent = dict(route.calls.last.request.url.params)
        assert sent == {"action": "agent_key.create", **FILTERS}

    @respx.mock
    def test_entry_without_actor_fields_parses(self) -> None:
        legacy = {**PAGE, "data": [{k: v for k, v in PAGE["data"][0].items() if not k.startswith("actor_")}]}
        respx.get(f"{BASE}/v1/audit-log").mock(return_value=httpx.Response(200, json=legacy))
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            page = client.audit_log.list()
        assert page.data[0].actor_type is None
        assert page.data[0].actor_label is None


class TestAsyncAuditLog:
    @respx.mock
    async def test_list_sends_actor_filters(self) -> None:
        route = respx.get(f"{BASE}/v1/audit-log").mock(
            return_value=httpx.Response(200, json=PAGE)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            page = await client.audit_log.list(**FILTERS)
        assert page.data[0].actor_type == "session"
        assert dict(route.calls.last.request.url.params) == FILTERS
