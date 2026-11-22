"""#2519: caller-supplied IDs stay inside their own URL path segment.

IDs used to be interpolated raw, so ``events.delete_by_id("../agents/agt_1")``
sent ``DELETE /v1/agents/agt_1`` (httpx resolves a literal ``..``), ``#``
dropped the rest of the path and ``?`` added a query string. Every ID now goes
through ``path_segment``: quoted as one segment, and ``""``, ``"."`` and
``".."`` refused before any request is sent.
"""

from __future__ import annotations

import contextlib
import inspect
from collections.abc import Callable
from typing import Any

import httpx
import pytest
import respx

from chronary import AsyncChronary, Chronary, ChronaryError, InvalidPathParameterError
from chronary._paths import path_segment

BASE = "https://api.chronary.ai"
ESCAPE = "../keys#x?y"
ESCAPE_ENCODED = "..%2Fkeys%23x%3Fy"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("evt_abc-123_XYZ", "evt_abc-123_XYZ"),
        ("11111111-2222-3333-4444-555555555555", "11111111-2222-3333-4444-555555555555"),
        ("../x", "..%2Fx"),
        ("%2e%2e", "%252e%252e"),
        ("a#b", "a%23b"),
        ("a?b=c", "a%3Fb%3Dc"),
        ("a/b", "a%2Fb"),
        ("...", "..."),
    ],
)
def test_path_segment_encodes(value: str, expected: str) -> None:
    assert path_segment(value) == expected


@pytest.mark.parametrize("value", ["", ".", ".."])
def test_path_segment_refuses(value: str) -> None:
    with pytest.raises(InvalidPathParameterError) as exc:
        path_segment(value)
    assert isinstance(exc.value, ChronaryError)
    assert isinstance(exc.value, ValueError)
    assert "No request was sent" in str(exc.value)


# Every method that puts a caller-supplied value into the path, with the
# prefix the request must stay under. Works for the sync and async clients.
Call = Callable[[Any, str], Any]
CALLS: list[tuple[str, Call, str]] = [
    ("agents.get", lambda c, i: c.agents.get(i), "/v1/agents/"),
    ("agents.update", lambda c, i: c.agents.update(i, name="n"), "/v1/agents/"),
    ("agents.delete", lambda c, i: c.agents.delete(i), "/v1/agents/"),
    (
        "agents.calendars.create",
        lambda c, i: c.agents.calendars.create(i, name="n", timezone="UTC"),
        "/v1/agents/",
    ),
    ("agents.calendars.list", lambda c, i: c.agents.calendars.list(i), "/v1/agents/"),
    ("agents.events.list", lambda c, i: c.agents.events.list(i), "/v1/agents/"),
    ("availability.get", lambda c, i: c.availability.get(i, start="a", end="b"), "/v1/agents/"),
    (
        "availability.get_calendar",
        lambda c, i: c.availability.get_calendar(i, start="a", end="b"),
        "/v1/calendars/",
    ),
    (
        "billing.upgrade_requests.get",
        lambda c, i: c.billing.upgrade_requests.get(i),
        "/v1/billing/upgrade-requests/",
    ),
    (
        "billing.upgrade_requests.cancel",
        lambda c, i: c.billing.upgrade_requests.cancel(i),
        "/v1/billing/upgrade-requests/",
    ),
    ("booking_pages.get", lambda c, i: c.booking_pages.get(i), "/v1/booking-pages/"),
    (
        "booking_pages.update",
        lambda c, i: c.booking_pages.update(i, title="t"),
        "/v1/booking-pages/",
    ),
    ("booking_pages.delete", lambda c, i: c.booking_pages.delete(i), "/v1/booking-pages/"),
    (
        "booking_pages.list_bookings",
        lambda c, i: c.booking_pages.list_bookings(i),
        "/v1/booking-pages/",
    ),
    (
        "booking_pages.rotate_slug",
        lambda c, i: c.booking_pages.rotate_slug(i),
        "/v1/booking-pages/",
    ),
    ("calendars.get", lambda c, i: c.calendars.get(i), "/v1/calendars/"),
    ("calendars.update", lambda c, i: c.calendars.update(i, name="n"), "/v1/calendars/"),
    ("calendars.delete", lambda c, i: c.calendars.delete(i), "/v1/calendars/"),
    (
        "calendars.rotate_ical_token",
        lambda c, i: c.calendars.rotate_ical_token(i),
        "/v1/calendars/",
    ),
    ("calendars.get_context", lambda c, i: c.calendars.get_context(i), "/v1/calendars/"),
    (
        "calendars.set_availability_rules",
        lambda c, i: c.calendars.set_availability_rules(i, buffer_before_minutes=5),
        "/v1/calendars/",
    ),
    (
        "calendars.get_availability_rules",
        lambda c, i: c.calendars.get_availability_rules(i),
        "/v1/calendars/",
    ),
    (
        "calendars.delete_availability_rules",
        lambda c, i: c.calendars.delete_availability_rules(i),
        "/v1/calendars/",
    ),
    (
        "connection_links.create",
        lambda c, i: c.connection_links.create(i, capabilities=["availability"]),
        "/v1/calendars/",
    ),
    ("connection_links.get", lambda c, i: c.connection_links.get(i), "/v1/connection-links/"),
    ("connection_links.cancel", lambda c, i: c.connection_links.cancel(i), "/v1/connection-links/"),
    (
        "events.create",
        lambda c, i: c.events.create(i, title="t", start_time="a", end_time="b"),
        "/v1/calendars/",
    ),
    ("events.list", lambda c, i: c.events.list(i), "/v1/calendars/"),
    ("events.get(calendar_id)", lambda c, i: c.events.get(i, "evt_1"), "/v1/calendars/"),
    ("events.get(event_id)", lambda c, i: c.events.get("cal_1", i), "/v1/calendars/cal_1/events/"),
    (
        "events.update(event_id)",
        lambda c, i: c.events.update("cal_1", i, title="t"),
        "/v1/calendars/cal_1/events/",
    ),
    (
        "events.delete(event_id)",
        lambda c, i: c.events.delete("cal_1", i),
        "/v1/calendars/cal_1/events/",
    ),
    ("events.get_by_id", lambda c, i: c.events.get_by_id(i), "/v1/events/"),
    ("events.update_by_id", lambda c, i: c.events.update_by_id(i, title="t"), "/v1/events/"),
    ("events.delete_by_id", lambda c, i: c.events.delete_by_id(i), "/v1/events/"),
    ("events.confirm", lambda c, i: c.events.confirm(i), "/v1/events/"),
    ("events.release", lambda c, i: c.events.release(i), "/v1/events/"),
    (
        "ical_subscriptions.create",
        lambda c, i: c.ical_subscriptions.create(
            i, calendar_id="cal_1", url="https://x.test/a.ics"
        ),
        "/v1/agents/",
    ),
    ("ical_subscriptions.list", lambda c, i: c.ical_subscriptions.list(i), "/v1/agents/"),
    ("ical_subscriptions.get", lambda c, i: c.ical_subscriptions.get(i), "/v1/ical-subscriptions/"),
    (
        "ical_subscriptions.update",
        lambda c, i: c.ical_subscriptions.update(i, label="l"),
        "/v1/ical-subscriptions/",
    ),
    (
        "ical_subscriptions.delete",
        lambda c, i: c.ical_subscriptions.delete(i),
        "/v1/ical-subscriptions/",
    ),
    (
        "ical_subscriptions.sync",
        lambda c, i: c.ical_subscriptions.sync(i),
        "/v1/ical-subscriptions/",
    ),
    (
        "ical_subscriptions.pause",
        lambda c, i: c.ical_subscriptions.pause(i),
        "/v1/ical-subscriptions/",
    ),
    (
        "ical_subscriptions.resume",
        lambda c, i: c.ical_subscriptions.resume(i),
        "/v1/ical-subscriptions/",
    ),
    ("keys.delete", lambda c, i: c.keys.delete(i), "/v1/keys/"),
    ("scheduling.get", lambda c, i: c.scheduling.get(i), "/v1/scheduling/proposals/"),
    (
        "scheduling.respond",
        lambda c, i: c.scheduling.respond(i, agent_id="agt_1", response="decline"),
        "/v1/scheduling/proposals/",
    ),
    ("scheduling.resolve", lambda c, i: c.scheduling.resolve(i), "/v1/scheduling/proposals/"),
    ("scheduling.cancel", lambda c, i: c.scheduling.cancel(i), "/v1/scheduling/proposals/"),
    ("webhooks.get", lambda c, i: c.webhooks.get(i), "/v1/webhooks/"),
    ("webhooks.update", lambda c, i: c.webhooks.update(i, active=True), "/v1/webhooks/"),
    ("webhooks.delete", lambda c, i: c.webhooks.delete(i), "/v1/webhooks/"),
    ("webhooks.list_deliveries", lambda c, i: c.webhooks.list_deliveries(i), "/v1/webhooks/"),
    (
        "webhooks.get_delivery(webhook_id)",
        lambda c, i: c.webhooks.get_delivery(i, "whd_1"),
        "/v1/webhooks/",
    ),
    (
        "webhooks.get_delivery(delivery_id)",
        lambda c, i: c.webhooks.get_delivery("whk_1", i),
        "/v1/webhooks/whk_1/deliveries/",
    ),
    (
        "webhooks.send_test",
        lambda c, i: c.webhooks.send_test(i, event_type="event.created"),
        "/v1/webhooks/",
    ),
    (
        "webhooks.replay_delivery(webhook_id)",
        lambda c, i: c.webhooks.replay_delivery(i, "whd_1"),
        "/v1/webhooks/",
    ),
    (
        "webhooks.replay_delivery(delivery_id)",
        lambda c, i: c.webhooks.replay_delivery("whk_1", i),
        "/v1/webhooks/whk_1/deliveries/",
    ),
    ("webhooks.rotate_secret", lambda c, i: c.webhooks.rotate_secret(i), "/v1/webhooks/"),
]
IDS = [name for name, _, _ in CALLS]


def _record(router: respx.Router) -> list[str]:
    sent: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request.url.raw_path.decode("ascii"))
        return httpx.Response(200, json={})

    router.route().mock(side_effect=handler)
    return sent


@pytest.mark.parametrize(("name", "call", "prefix"), CALLS, ids=IDS)
def test_sync_keeps_id_in_one_segment(name: str, call: Call, prefix: str) -> None:
    with respx.mock(assert_all_called=False) as router:
        sent = _record(router)
        # The stub answers {}; only the request path matters.
        with (
            Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client,
            contextlib.suppress(ChronaryError, ValueError, TypeError, KeyError),
        ):
            call(client, ESCAPE)
        assert len(sent) == 1, name
        assert sent[0].split("?")[0].startswith(prefix + ESCAPE_ENCODED), sent[0]


@pytest.mark.parametrize(("name", "call", "prefix"), CALLS, ids=IDS)
def test_sync_refuses_dot_segment(name: str, call: Call, prefix: str) -> None:
    with respx.mock(assert_all_called=False) as router:
        sent = _record(router)
        with (
            Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client,
            pytest.raises(InvalidPathParameterError),
        ):
            call(client, "..")
        assert sent == [], name


async def _run(result: Any) -> Any:
    return await result if inspect.isawaitable(result) else result


@pytest.mark.parametrize(("name", "call", "prefix"), CALLS, ids=IDS)
async def test_async_keeps_id_in_one_segment(name: str, call: Call, prefix: str) -> None:
    with respx.mock(assert_all_called=False) as router:
        sent = _record(router)
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client:
            # the stub answers {}; only the request path matters
            with contextlib.suppress(ChronaryError, ValueError, TypeError, KeyError):
                await _run(call(client, ESCAPE))
        assert len(sent) == 1, name
        assert sent[0].split("?")[0].startswith(prefix + ESCAPE_ENCODED), sent[0]


@pytest.mark.parametrize(("name", "call", "prefix"), CALLS, ids=IDS)
async def test_async_refuses_dot_segment(name: str, call: Call, prefix: str) -> None:
    with respx.mock(assert_all_called=False) as router:
        sent = _record(router)
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client:
            for bad in ("", ".", ".."):
                with pytest.raises(InvalidPathParameterError):
                    await _run(call(client, bad))
        assert sent == [], name


def test_issue_proof_cases() -> None:
    """The exact cases from #2519."""
    with respx.mock(assert_all_called=False) as router:
        sent = _record(router)
        with Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client:
            for fn in (
                lambda: client.events.delete_by_id("../agents/agt_1"),
                lambda: client.events.get_by_id("%2e%2e/keys"),
                lambda: client.events.delete("../webhooks/whk_1#", "evt_x"),
                lambda: client.events.get_by_id("evt_1?expand=all"),
            ):
                with contextlib.suppress(ChronaryError, ValueError):
                    fn()
        assert sent == [
            "/v1/events/..%2Fagents%2Fagt_1",
            "/v1/events/%252e%252e%2Fkeys",
            "/v1/calendars/..%2Fwebhooks%2Fwhk_1%23/events/evt_x",
            "/v1/events/evt_1%3Fexpand%3Dall",
        ]
