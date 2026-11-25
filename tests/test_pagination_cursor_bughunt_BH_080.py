"""bughunt-BH-080 (#2691): auto-pagination past the API's 10,000-row offset cap.

With NOC_QUERY_CAPS on, every list rejects ``offset > 10000`` with 400
validation_error. ``auto_paging_iter()`` paged by offset only, so iterating more
than 10,000 rows raised partway, even on lists that return ``next_cursor``. It
now follows ``next_cursor`` where the list has one.
"""

from __future__ import annotations

import base64
from typing import Any

import httpx
import pytest
import respx

from chronary import APIError, AsyncChronary, Chronary

BASE = "https://api.chronary.ai"
MAX_OFFSET = 10_000
ROWS = 12_000

AGENT = {
    "name": "Agent",
    "type": "ai",
    "description": None,
    "status": "active",
    "metadata": {},
    "createdAt": "2026-01-15T10:30:00Z",
    "updatedAt": "2026-01-15T10:30:00Z",
}
CALENDAR = {
    "orgId": "org_1",
    "name": "Cal",
    "timezone": "UTC",
    "agentId": None,
    "metadata": {},
    "agent_status": "idle",
    "ical_url": "https://ical.chronary.ai/ical/T.ics",
    "externalId": None,
    "provider": None,
    "deletedAt": None,
    "createdAt": "2026-01-15T10:30:00Z",
    "updatedAt": "2026-01-15T10:30:00Z",
}
EVENT = {
    "calendarId": "cal_1",
    "title": "Sync",
    "description": None,
    "startTime": "2026-03-28T14:00:00Z",
    "endTime": "2026-03-28T14:30:00Z",
    "allDay": False,
    "status": "confirmed",
    "source": "internal",
    "metadata": {},
    "createdAt": "2026-01-15T10:30:00Z",
    "updatedAt": "2026-01-15T10:30:00Z",
}


def _enc(i: int) -> str:
    return base64.b64encode(str(i).encode()).decode()


def _validation_error(message: str) -> httpx.Response:
    return httpx.Response(400, json={"error": {"type": "validation_error", "message": message}})


class CappedApi:
    """A fake API holding ROWS rows that enforces the deep-offset cap.

    Cursor lists return ``next_cursor`` (null on the last page) and accept
    ``cursor``, rejecting it with a non-zero offset as the API does.
    """

    def __init__(self, template: dict[str, Any], *, with_cursor: bool) -> None:
        self.template = template
        self.with_cursor = with_cursor
        self.offsets: list[int] = []
        self.cursors: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        qp = request.url.params
        limit = int(qp.get("limit", "50"))
        offset = int(qp.get("offset", "0"))
        cursor = qp.get("cursor")
        if offset > MAX_OFFSET:
            return _validation_error("offset must be at most 10000")
        if cursor is not None and (not self.with_cursor or offset > 0):
            return _validation_error("cursor and offset cannot be combined")
        self.offsets.append(offset)
        if cursor is not None:
            self.cursors.append(cursor)
        start = int(base64.b64decode(cursor)) if cursor is not None else offset
        stop = min(start + limit, ROWS)
        data = [{**self.template, "id": f"row_{i}"} for i in range(start, stop)]
        body: dict[str, Any] = {"data": data, "total": ROWS, "limit": limit, "offset": offset}
        if self.with_cursor:
            body["next_cursor"] = _enc(stop) if stop < ROWS else None
        return httpx.Response(200, json=body)


class TestSyncCursorPaging:
    @respx.mock
    def test_list_all_events_yields_all_rows_by_cursor(self) -> None:
        api = CappedApi(EVENT, with_cursor=True)
        respx.get(f"{BASE}/v1/events").mock(side_effect=api)
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            ids = [e.id for e in client.events.list_all(limit=100).auto_paging_iter()]
        assert len(ids) == ROWS
        assert len(set(ids)) == ROWS
        assert max(api.offsets) == 0
        assert len(api.cursors) == ROWS // 100 - 1

    @respx.mock
    def test_agents_and_calendars_follow_next_cursor(self) -> None:
        respx.get(f"{BASE}/v1/agents").mock(side_effect=CappedApi(AGENT, with_cursor=True))
        respx.get(f"{BASE}/v1/calendars").mock(side_effect=CappedApi(CALENDAR, with_cursor=True))
        respx.get(f"{BASE}/v1/agents/agt_1/calendars").mock(
            side_effect=CappedApi(CALENDAR, with_cursor=True)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            assert len(list(client.agents.list(limit=200).auto_paging_iter())) == ROWS
            assert len(list(client.calendars.list(limit=200).auto_paging_iter())) == ROWS
            agent_cals = client.agents.calendars.list("agt_1", limit=200)
            assert len(list(agent_cals.auto_paging_iter())) == ROWS

    @respx.mock
    def test_drops_starting_offset_once_on_a_cursor(self) -> None:
        api = CappedApi(EVENT, with_cursor=True)
        respx.get(f"{BASE}/v1/events").mock(side_effect=api)
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            ids = [e.id for e in client.events.list_all(limit=100, offset=500).auto_paging_iter()]
        assert len(ids) == ROWS - 500
        assert ids[0] == "row_500"
        assert api.offsets[0] == 500
        assert set(api.offsets[1:]) == {0}

    @respx.mock
    def test_cursor_kwarg_and_page_fields(self) -> None:
        respx.get(f"{BASE}/v1/agents").mock(side_effect=CappedApi(AGENT, with_cursor=True))
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            first = client.agents.list(limit=100)
            assert first.next_cursor == _enc(100)
            assert first.has_more
            last = client.agents.list(limit=100, cursor=_enc(11_900))
            assert last.next_cursor is None
            assert not last.has_more
            assert last.data[0].id == "row_11900"
            assert len(list(last.auto_paging_iter())) == 100

    @respx.mock
    def test_offset_only_list_still_pages_by_offset(self) -> None:
        api = CappedApi(EVENT, with_cursor=False)
        respx.get(f"{BASE}/v1/calendars/cal_1/events").mock(side_effect=api)
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = client.events.list("cal_1", limit=2000)
            assert pager.next_cursor is None
            ids = [e.id for e in pager.auto_paging_iter()]
        assert len(ids) == ROWS
        assert api.cursors == []
        assert api.offsets == [0, 2000, 4000, 6000, 8000, 10_000]


class TestAsyncCursorPaging:
    @pytest.mark.asyncio
    @respx.mock
    async def test_list_all_events_yields_all_rows_by_cursor(self) -> None:
        api = CappedApi(EVENT, with_cursor=True)
        respx.get(f"{BASE}/v1/events").mock(side_effect=api)
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = await client.events.list_all(limit=100)
            ids = [e.id async for e in pager.auto_paging_iter()]
        assert len(ids) == ROWS
        assert max(api.offsets) == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_agents_and_calendars_follow_next_cursor(self) -> None:
        respx.get(f"{BASE}/v1/agents").mock(side_effect=CappedApi(AGENT, with_cursor=True))
        respx.get(f"{BASE}/v1/calendars").mock(side_effect=CappedApi(CALENDAR, with_cursor=True))
        respx.get(f"{BASE}/v1/agents/agt_1/calendars").mock(
            side_effect=CappedApi(CALENDAR, with_cursor=True)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            agents = await client.agents.list(limit=200, cursor=_enc(11_000))
            assert len([a async for a in agents.auto_paging_iter()]) == 1000
            cals = await client.calendars.list(limit=200)
            assert len([c async for c in cals.auto_paging_iter()]) == ROWS
            agent_cals = await client.agents.calendars.list("agt_1", limit=200)
            assert len([c async for c in agent_cals.auto_paging_iter()]) == ROWS


class TestRepeatedCursorGuard:
    """Review of #2748: a list that hands back the cursor just sent must not loop."""

    @respx.mock
    def test_repeated_next_cursor_raises(self) -> None:
        body = {
            "data": [{**AGENT, "id": "a"}],
            "total": 5,
            "limit": 1,
            "offset": 0,
            "next_cursor": "same",
        }
        route = respx.get(f"{BASE}/v1/agents").mock(return_value=httpx.Response(200, json=body))
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = client.agents.list(limit=1)
            with pytest.raises(APIError, match="same next_cursor"):
                list(pager.auto_paging_iter())
        assert route.call_count == 2
