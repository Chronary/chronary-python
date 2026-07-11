from __future__ import annotations

import httpx
import respx

from chronary import AsyncChronary, Chronary, Event
from chronary.pagination import AsyncPager, SyncPager

BASE = "https://api.chronary.ai"

EVENT_DATA = {
    "id": "evt_abc123",
    "calendarId": "cal_abc123",
    "title": "Strategy Sync",
    "description": "Discuss Q2 alignment",
    "startTime": "2026-03-28T14:00:00Z",
    "endTime": "2026-03-28T14:30:00Z",
    "allDay": False,
    "status": "confirmed",
    "source": "internal",
    "metadata": {},
    "createdAt": "2026-01-15T10:30:00Z",
    "updatedAt": "2026-01-15T10:30:00Z",
}

LIST_RESPONSE = {
    "data": [EVENT_DATA],
    "total": 1,
    "limit": 50,
    "offset": 0,
}

RECURRING_EVENT_DATA = {
    **EVENT_DATA,
    "recurrenceRule": "FREQ=WEEKLY;BYDAY=MO,WE;COUNT=12",
    "recurrenceExdates": [],
}

EXPANDED_INSTANCE_DATA = {
    **RECURRING_EVENT_DATA,
    "recurringEventId": "evt_abc123",
    "originalStartTime": "2026-03-30T14:00:00Z",
    "startTime": "2026-03-30T14:00:00Z",
    "endTime": "2026-03-30T14:30:00Z",
}

EXPANDED_LIST_RESPONSE = {
    "data": [EXPANDED_INSTANCE_DATA],
    "total": 1,
    "limit": 50,
    "offset": 0,
}


# ---------------------------------------------------------------------------
# Sync tests
# ---------------------------------------------------------------------------


class TestSyncEvents:
    @respx.mock
    def test_create(self) -> None:
        respx.post(f"{BASE}/v1/calendars/cal_abc123/events").mock(
            return_value=httpx.Response(201, json=EVENT_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.create(
                "cal_abc123",
                title="Strategy Sync",
                start_time="2026-03-28T14:00:00Z",
                end_time="2026-03-28T14:30:00Z",
            )
            assert isinstance(evt, Event)
            assert evt.id == "evt_abc123"
            assert evt.calendar_id == "cal_abc123"
            assert evt.title == "Strategy Sync"

    @respx.mock
    def test_list(self) -> None:
        respx.get(f"{BASE}/v1/calendars/cal_abc123/events").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = client.events.list("cal_abc123")
            assert isinstance(pager, SyncPager)
            assert len(pager.data) == 1

    @respx.mock
    def test_get(self) -> None:
        respx.get(f"{BASE}/v1/calendars/cal_abc123/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=EVENT_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.get("cal_abc123", "evt_abc123")
            assert evt.id == "evt_abc123"

    @respx.mock
    def test_update(self) -> None:
        updated = {**EVENT_DATA, "title": "Renamed"}
        respx.patch(f"{BASE}/v1/calendars/cal_abc123/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.update("cal_abc123", "evt_abc123", title="Renamed")
            assert evt.title == "Renamed"

    @respx.mock
    def test_update_description_to_none(self) -> None:
        updated = {**EVENT_DATA, "description": None}
        route = respx.patch(f"{BASE}/v1/calendars/cal_abc123/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.update("cal_abc123", "evt_abc123", description=None)
            assert evt.description is None
            sent_body = route.calls[0].request.content
            assert b'"description"' in sent_body

    @respx.mock
    def test_delete(self) -> None:
        respx.delete(f"{BASE}/v1/calendars/cal_abc123/events/evt_abc123").mock(
            return_value=httpx.Response(204)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.events.delete("cal_abc123", "evt_abc123")
            assert result is None

    @respx.mock
    def test_request_id(self) -> None:
        respx.post(f"{BASE}/v1/calendars/cal_abc123/events").mock(
            return_value=httpx.Response(
                201, json=EVENT_DATA, headers={"X-Request-Id": "req_evt_1"}
            )
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.create(
                "cal_abc123",
                title="Strategy Sync",
                start_time="2026-03-28T14:00:00Z",
                end_time="2026-03-28T14:30:00Z",
            )
            assert evt._request_id == "req_evt_1"

    @respx.mock
    def test_confirm(self) -> None:
        confirmed = {**EVENT_DATA, "status": "confirmed", "holdExpiresAt": None}
        respx.put(f"{BASE}/v1/events/evt_abc123/confirm").mock(
            return_value=httpx.Response(200, json=confirmed)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.confirm("evt_abc123")
            assert isinstance(evt, Event)
            assert evt.status == "confirmed"

    @respx.mock
    def test_release(self) -> None:
        released = {**EVENT_DATA, "status": "cancelled"}
        respx.put(f"{BASE}/v1/events/evt_abc123/release").mock(
            return_value=httpx.Response(200, json=released)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.release("evt_abc123")
            assert isinstance(evt, Event)
            assert evt.status == "cancelled"

    @respx.mock
    def test_get_by_id(self) -> None:
        respx.get(f"{BASE}/v1/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=EVENT_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.get_by_id("evt_abc123")
            assert evt.id == "evt_abc123"

    @respx.mock
    def test_update_by_id(self) -> None:
        updated = {**EVENT_DATA, "title": "Renamed"}
        respx.patch(f"{BASE}/v1/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.update_by_id("evt_abc123", title="Renamed")
            assert evt.title == "Renamed"

    @respx.mock
    def test_delete_by_id(self) -> None:
        respx.delete(f"{BASE}/v1/events/evt_abc123").mock(
            return_value=httpx.Response(204)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.events.delete_by_id("evt_abc123")
            assert result is None

    @respx.mock
    def test_create_hold(self) -> None:
        hold = {
            **EVENT_DATA,
            "status": "hold",
            "holdExpiresAt": "2099-01-01T10:05:00Z",
            "holdPriority": 10,
        }
        respx.post(f"{BASE}/v1/calendars/cal_abc123/events").mock(
            return_value=httpx.Response(201, json=hold)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.create(
                "cal_abc123",
                title="hold slot",
                start_time="2099-01-01T10:00:00Z",
                end_time="2099-01-01T10:30:00Z",
                status="hold",
                hold_expires_at="2099-01-01T10:05:00Z",
                hold_priority=10,
            )
            assert evt.status == "hold"
            assert evt.hold_priority == 10

    @respx.mock
    def test_create_with_reminders(self) -> None:
        created = {**EVENT_DATA, "reminders": [10, 1440]}
        route = respx.post(f"{BASE}/v1/calendars/cal_abc123/events").mock(
            return_value=httpx.Response(201, json=created)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.create(
                "cal_abc123",
                title="Strategy Sync",
                start_time="2026-03-28T14:00:00Z",
                end_time="2026-03-28T14:30:00Z",
                reminders=[10, 1440],
            )
            assert evt.reminders == [10, 1440]
            assert b'"reminders"' in route.calls[0].request.content

    @respx.mock
    def test_update_reminders_to_empty(self) -> None:
        updated = {**EVENT_DATA, "reminders": []}
        route = respx.patch(f"{BASE}/v1/calendars/cal_abc123/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.update("cal_abc123", "evt_abc123", reminders=[])
            assert evt.reminders == []
            assert b'"reminders"' in route.calls[0].request.content

    @respx.mock
    def test_create_recurring(self) -> None:
        route = respx.post(f"{BASE}/v1/calendars/cal_abc123/events").mock(
            return_value=httpx.Response(201, json=RECURRING_EVENT_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.create(
                "cal_abc123",
                title="Strategy Sync",
                start_time="2026-03-28T14:00:00Z",
                end_time="2026-03-28T14:30:00Z",
                recurrence_rule="FREQ=WEEKLY;BYDAY=MO,WE;COUNT=12",
            )
            assert evt.recurrence_rule == "FREQ=WEEKLY;BYDAY=MO,WE;COUNT=12"
            assert evt.recurrence_exdates == []
            assert b'"recurrence_rule"' in route.calls[0].request.content

    @respx.mock
    def test_create_without_recurrence_omits_field(self) -> None:
        route = respx.post(f"{BASE}/v1/calendars/cal_abc123/events").mock(
            return_value=httpx.Response(201, json=EVENT_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.create(
                "cal_abc123",
                title="Strategy Sync",
                start_time="2026-03-28T14:00:00Z",
                end_time="2026-03-28T14:30:00Z",
            )
            assert evt.recurrence_rule is None
            assert b'"recurrence_rule"' not in route.calls[0].request.content

    @respx.mock
    def test_update_recurrence_rule(self) -> None:
        updated = {**RECURRING_EVENT_DATA, "recurrenceRule": "FREQ=DAILY;COUNT=5"}
        route = respx.patch(f"{BASE}/v1/calendars/cal_abc123/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.update(
                "cal_abc123", "evt_abc123", recurrence_rule="FREQ=DAILY;COUNT=5"
            )
            assert evt.recurrence_rule == "FREQ=DAILY;COUNT=5"
            assert b'"recurrence_rule"' in route.calls[0].request.content

    @respx.mock
    def test_update_recurrence_rule_to_none(self) -> None:
        updated = {**EVENT_DATA, "recurrenceRule": None}
        route = respx.patch(f"{BASE}/v1/calendars/cal_abc123/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.update("cal_abc123", "evt_abc123", recurrence_rule=None)
            assert evt.recurrence_rule is None
            sent_body = route.calls[0].request.content
            assert b'"recurrence_rule"' in sent_body

    @respx.mock
    def test_update_recurrence_rule_omitted(self) -> None:
        route = respx.patch(f"{BASE}/v1/calendars/cal_abc123/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=EVENT_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            client.events.update("cal_abc123", "evt_abc123", title="Renamed")
            assert b'"recurrence_rule"' not in route.calls[0].request.content

    @respx.mock
    def test_list_expand(self) -> None:
        route = respx.get(f"{BASE}/v1/calendars/cal_abc123/events").mock(
            return_value=httpx.Response(200, json=EXPANDED_LIST_RESPONSE)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = client.events.list(
                "cal_abc123",
                start_after="2026-03-28T00:00:00Z",
                start_before="2026-04-28T00:00:00Z",
                expand=True,
            )
            assert len(pager.data) == 1
            instance = pager.data[0]
            assert instance.recurring_event_id == "evt_abc123"
            assert instance.original_start_time is not None
            sent_url = str(route.calls[0].request.url)
            assert "expand=true" in sent_url

    @respx.mock
    def test_list_expand_false_sends_string(self) -> None:
        route = respx.get(f"{BASE}/v1/calendars/cal_abc123/events").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            client.events.list("cal_abc123", expand=False)
            assert "expand=false" in str(route.calls[0].request.url)

    @respx.mock
    def test_list_expand_omitted(self) -> None:
        route = respx.get(f"{BASE}/v1/calendars/cal_abc123/events").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            client.events.list("cal_abc123")
            assert "expand" not in str(route.calls[0].request.url)

    @respx.mock
    def test_delete_occurrence(self) -> None:
        updated_master = {
            **RECURRING_EVENT_DATA,
            "recurrenceExdates": ["2026-03-30T14:00:00Z"],
        }
        route = respx.delete(f"{BASE}/v1/calendars/cal_abc123/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=updated_master)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.delete(
                "cal_abc123", "evt_abc123", occurrence_start="2026-03-30T14:00:00Z"
            )
            assert isinstance(evt, Event)
            assert evt.recurrence_exdates == ["2026-03-30T14:00:00Z"]
            sent_url = str(route.calls[0].request.url)
            assert "occurrence_start=" in sent_url

    @respx.mock
    def test_delete_by_id_occurrence(self) -> None:
        updated_master = {
            **RECURRING_EVENT_DATA,
            "recurrenceExdates": ["2026-03-30T14:00:00Z"],
        }
        route = respx.delete(f"{BASE}/v1/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=updated_master)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = client.events.delete_by_id(
                "evt_abc123", occurrence_start="2026-03-30T14:00:00Z"
            )
            assert isinstance(evt, Event)
            assert evt.recurrence_exdates == ["2026-03-30T14:00:00Z"]
            assert "occurrence_start=" in str(route.calls[0].request.url)

    @respx.mock
    def test_delete_without_occurrence_sends_no_param(self) -> None:
        route = respx.delete(f"{BASE}/v1/calendars/cal_abc123/events/evt_abc123").mock(
            return_value=httpx.Response(204)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = client.events.delete("cal_abc123", "evt_abc123")
            assert result is None
            assert "occurrence_start" not in str(route.calls[0].request.url)


# ---------------------------------------------------------------------------
# Agent-scoped sync tests
# ---------------------------------------------------------------------------


class TestSyncAgentEvents:
    @respx.mock
    def test_list(self) -> None:
        respx.get(f"{BASE}/v1/agents/agt_abc123/events").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = client.agents.events.list("agt_abc123")
            assert isinstance(pager, SyncPager)
            assert len(pager.data) == 1
            assert pager.data[0].id == "evt_abc123"

    @respx.mock
    def test_list_expand(self) -> None:
        route = respx.get(f"{BASE}/v1/agents/agt_abc123/events").mock(
            return_value=httpx.Response(200, json=EXPANDED_LIST_RESPONSE)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = client.agents.events.list(
                "agt_abc123",
                start_after="2026-03-28T00:00:00Z",
                start_before="2026-04-28T00:00:00Z",
                expand=True,
            )
            assert pager.data[0].recurring_event_id == "evt_abc123"
            assert "expand=true" in str(route.calls[0].request.url)


# ---------------------------------------------------------------------------
# Async tests
# ---------------------------------------------------------------------------


class TestAsyncEvents:
    @respx.mock
    async def test_create(self) -> None:
        respx.post(f"{BASE}/v1/calendars/cal_abc123/events").mock(
            return_value=httpx.Response(201, json=EVENT_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = await client.events.create(
                "cal_abc123",
                title="Strategy Sync",
                start_time="2026-03-28T14:00:00Z",
                end_time="2026-03-28T14:30:00Z",
            )
            assert isinstance(evt, Event)
            assert evt.id == "evt_abc123"

    @respx.mock
    async def test_list(self) -> None:
        respx.get(f"{BASE}/v1/calendars/cal_abc123/events").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = await client.events.list("cal_abc123")
            assert isinstance(pager, AsyncPager)
            assert len(pager.data) == 1

    @respx.mock
    async def test_get(self) -> None:
        respx.get(f"{BASE}/v1/calendars/cal_abc123/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=EVENT_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = await client.events.get("cal_abc123", "evt_abc123")
            assert evt.id == "evt_abc123"

    @respx.mock
    async def test_update(self) -> None:
        updated = {**EVENT_DATA, "title": "Renamed"}
        respx.patch(f"{BASE}/v1/calendars/cal_abc123/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = await client.events.update("cal_abc123", "evt_abc123", title="Renamed")
            assert evt.title == "Renamed"

    @respx.mock
    async def test_delete(self) -> None:
        respx.delete(f"{BASE}/v1/calendars/cal_abc123/events/evt_abc123").mock(
            return_value=httpx.Response(204)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = await client.events.delete("cal_abc123", "evt_abc123")
            assert result is None

    @respx.mock
    async def test_get_by_id(self) -> None:
        respx.get(f"{BASE}/v1/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=EVENT_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = await client.events.get_by_id("evt_abc123")
            assert evt.id == "evt_abc123"

    @respx.mock
    async def test_update_by_id(self) -> None:
        updated = {**EVENT_DATA, "title": "Renamed"}
        respx.patch(f"{BASE}/v1/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = await client.events.update_by_id("evt_abc123", title="Renamed")
            assert evt.title == "Renamed"

    @respx.mock
    async def test_delete_by_id(self) -> None:
        respx.delete(f"{BASE}/v1/events/evt_abc123").mock(
            return_value=httpx.Response(204)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            result = await client.events.delete_by_id("evt_abc123")
            assert result is None

    @respx.mock
    async def test_confirm(self) -> None:
        confirmed = {**EVENT_DATA, "status": "confirmed", "holdExpiresAt": None}
        respx.put(f"{BASE}/v1/events/evt_abc123/confirm").mock(
            return_value=httpx.Response(200, json=confirmed)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = await client.events.confirm("evt_abc123")
            assert evt.status == "confirmed"

    @respx.mock
    async def test_release(self) -> None:
        released = {**EVENT_DATA, "status": "cancelled"}
        respx.put(f"{BASE}/v1/events/evt_abc123/release").mock(
            return_value=httpx.Response(200, json=released)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = await client.events.release("evt_abc123")
            assert evt.status == "cancelled"

    @respx.mock
    async def test_create_recurring(self) -> None:
        route = respx.post(f"{BASE}/v1/calendars/cal_abc123/events").mock(
            return_value=httpx.Response(201, json=RECURRING_EVENT_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = await client.events.create(
                "cal_abc123",
                title="Strategy Sync",
                start_time="2026-03-28T14:00:00Z",
                end_time="2026-03-28T14:30:00Z",
                recurrence_rule="FREQ=WEEKLY;BYDAY=MO,WE;COUNT=12",
            )
            assert evt.recurrence_rule == "FREQ=WEEKLY;BYDAY=MO,WE;COUNT=12"
            assert b'"recurrence_rule"' in route.calls[0].request.content

    @respx.mock
    async def test_update_recurrence_rule_to_none(self) -> None:
        updated = {**EVENT_DATA, "recurrenceRule": None}
        route = respx.patch(f"{BASE}/v1/calendars/cal_abc123/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = await client.events.update(
                "cal_abc123", "evt_abc123", recurrence_rule=None
            )
            assert evt.recurrence_rule is None
            assert b'"recurrence_rule"' in route.calls[0].request.content

    @respx.mock
    async def test_update_by_id_recurrence_rule(self) -> None:
        updated = {**RECURRING_EVENT_DATA, "recurrenceRule": "FREQ=DAILY;COUNT=5"}
        route = respx.patch(f"{BASE}/v1/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = await client.events.update_by_id(
                "evt_abc123", recurrence_rule="FREQ=DAILY;COUNT=5"
            )
            assert evt.recurrence_rule == "FREQ=DAILY;COUNT=5"
            assert b'"recurrence_rule"' in route.calls[0].request.content

    @respx.mock
    async def test_list_expand(self) -> None:
        route = respx.get(f"{BASE}/v1/calendars/cal_abc123/events").mock(
            return_value=httpx.Response(200, json=EXPANDED_LIST_RESPONSE)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = await client.events.list(
                "cal_abc123",
                start_after="2026-03-28T00:00:00Z",
                start_before="2026-04-28T00:00:00Z",
                expand=True,
            )
            assert pager.data[0].recurring_event_id == "evt_abc123"
            assert "expand=true" in str(route.calls[0].request.url)

    @respx.mock
    async def test_delete_occurrence(self) -> None:
        updated_master = {
            **RECURRING_EVENT_DATA,
            "recurrenceExdates": ["2026-03-30T14:00:00Z"],
        }
        route = respx.delete(f"{BASE}/v1/calendars/cal_abc123/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=updated_master)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = await client.events.delete(
                "cal_abc123", "evt_abc123", occurrence_start="2026-03-30T14:00:00Z"
            )
            assert isinstance(evt, Event)
            assert evt.recurrence_exdates == ["2026-03-30T14:00:00Z"]
            assert "occurrence_start=" in str(route.calls[0].request.url)

    @respx.mock
    async def test_delete_by_id_occurrence(self) -> None:
        updated_master = {
            **RECURRING_EVENT_DATA,
            "recurrenceExdates": ["2026-03-30T14:00:00Z"],
        }
        respx.delete(f"{BASE}/v1/events/evt_abc123").mock(
            return_value=httpx.Response(200, json=updated_master)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            evt = await client.events.delete_by_id(
                "evt_abc123", occurrence_start="2026-03-30T14:00:00Z"
            )
            assert isinstance(evt, Event)
            assert evt.recurrence_exdates == ["2026-03-30T14:00:00Z"]


class TestAsyncAgentEvents:
    @respx.mock
    async def test_list(self) -> None:
        respx.get(f"{BASE}/v1/agents/agt_abc123/events").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = await client.agents.events.list("agt_abc123")
            assert isinstance(pager, AsyncPager)
            assert len(pager.data) == 1

    @respx.mock
    async def test_list_expand(self) -> None:
        route = respx.get(f"{BASE}/v1/agents/agt_abc123/events").mock(
            return_value=httpx.Response(200, json=EXPANDED_LIST_RESPONSE)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = await client.agents.events.list(
                "agt_abc123",
                start_after="2026-03-28T00:00:00Z",
                start_before="2026-04-28T00:00:00Z",
                expand=True,
            )
            assert pager.data[0].recurring_event_id == "evt_abc123"
            assert "expand=true" in str(route.calls[0].request.url)
