from __future__ import annotations

import httpx
import respx

from chronary import AsyncChronary, BookingPage, Chronary
from chronary.pagination import AsyncPager, SyncPager

BASE = "https://api.chronary.ai"

BOOKING_PAGE_DATA = {
    "id": "bkp_abc123",
    "org_id": "org_abc123",
    "calendar_id": "cal_abc123",
    "agent_id": "agt_abc123",
    "slug": "a1b2c3d4e5f6g7h8i9j0k1",
    "title": "Intro call",
    "description": None,
    "duration_minutes": 30,
    "buffer_minutes": 0,
    "window_days": 14,
    "min_notice_minutes": 0,
    "timezone": "UTC",
    "availability_constraints": None,
    "active": True,
    "bookings_count": 0,
    "booking_url": "https://api.chronary.ai/book/a1b2c3d4e5f6g7h8i9j0k1",
    "created_at": "2026-07-14T10:00:00Z",
    "updated_at": "2026-07-14T10:00:00Z",
}

LIST_RESPONSE = {"data": [BOOKING_PAGE_DATA], "total": 1, "limit": 50, "offset": 0}


class TestSyncBookingPages:
    @respx.mock
    def test_create(self) -> None:
        respx.post(f"{BASE}/v1/booking-pages").mock(
            return_value=httpx.Response(201, json=BOOKING_PAGE_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            page = client.booking_pages.create(calendar_id="cal_abc123", title="Intro call")
            assert isinstance(page, BookingPage)
            assert page.id == "bkp_abc123"
            assert page.slug == "a1b2c3d4e5f6g7h8i9j0k1"
            assert page.booking_url.endswith("/book/a1b2c3d4e5f6g7h8i9j0k1")
            assert page.duration_minutes == 30

    @respx.mock
    def test_create_with_all_options(self) -> None:
        created = {
            **BOOKING_PAGE_DATA,
            "description": "A quick chat",
            "duration_minutes": 45,
            "buffer_minutes": 10,
            "window_days": 30,
            "min_notice_minutes": 120,
            "timezone": "America/New_York",
            "availability_constraints": {"mon": {"start": "09:00", "end": "17:00"}},
            "active": False,
        }
        route = respx.post(f"{BASE}/v1/booking-pages").mock(
            return_value=httpx.Response(201, json=created)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            page = client.booking_pages.create(
                calendar_id="cal_abc123",
                title="Intro call",
                description="A quick chat",
                duration_minutes=45,
                buffer_minutes=10,
                window_days=30,
                min_notice_minutes=120,
                timezone="America/New_York",
                availability_constraints={"mon": {"start": "09:00", "end": "17:00"}},
                active=False,
            )
            assert page.duration_minutes == 45
            assert page.availability_constraints == {"mon": {"start": "09:00", "end": "17:00"}}
            body = route.calls[0].request.content
            assert b'"buffer_minutes"' in body
            assert b'"availability_constraints"' in body
            assert b'"active"' in body

    @respx.mock
    def test_list(self) -> None:
        respx.get(f"{BASE}/v1/booking-pages").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = client.booking_pages.list()
            assert isinstance(pager, SyncPager)
            assert len(pager.data) == 1
            assert pager.data[0].id == "bkp_abc123"

    @respx.mock
    def test_get(self) -> None:
        respx.get(f"{BASE}/v1/booking-pages/bkp_abc123").mock(
            return_value=httpx.Response(200, json=BOOKING_PAGE_DATA, headers={"X-Request-Id": "req_bkp_1"})
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            page = client.booking_pages.get("bkp_abc123")
            assert page.id == "bkp_abc123"
            assert page.calendar_id == "cal_abc123"
            assert page._request_id == "req_bkp_1"

    @respx.mock
    def test_update(self) -> None:
        updated = {**BOOKING_PAGE_DATA, "title": "Renamed", "active": False}
        route = respx.patch(f"{BASE}/v1/booking-pages/bkp_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            page = client.booking_pages.update(
                "bkp_abc123",
                title="Renamed",
                duration_minutes=60,
                buffer_minutes=5,
                window_days=7,
                min_notice_minutes=30,
                timezone="UTC",
                availability_constraints=None,
                active=False,
            )
            assert page.title == "Renamed"
            body = route.calls[0].request.content
            assert b'"duration_minutes"' in body
            assert b'"availability_constraints"' in body  # explicit None still sent

    @respx.mock
    def test_update_description(self) -> None:
        updated = {**BOOKING_PAGE_DATA, "description": "New desc"}
        route = respx.patch(f"{BASE}/v1/booking-pages/bkp_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            page = client.booking_pages.update("bkp_abc123", description="New desc")
            assert page.description == "New desc"
            assert b'"description"' in route.calls[0].request.content

    @respx.mock
    def test_delete(self) -> None:
        respx.delete(f"{BASE}/v1/booking-pages/bkp_abc123").mock(
            return_value=httpx.Response(204)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            assert client.booking_pages.delete("bkp_abc123") is None


class TestAsyncBookingPages:
    @respx.mock
    async def test_create(self) -> None:
        respx.post(f"{BASE}/v1/booking-pages").mock(
            return_value=httpx.Response(201, json=BOOKING_PAGE_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            page = await client.booking_pages.create(calendar_id="cal_abc123", title="Intro call")
            assert isinstance(page, BookingPage)
            assert page.id == "bkp_abc123"

    @respx.mock
    async def test_create_with_options(self) -> None:
        created = {**BOOKING_PAGE_DATA, "duration_minutes": 45}
        respx.post(f"{BASE}/v1/booking-pages").mock(
            return_value=httpx.Response(201, json=created)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            page = await client.booking_pages.create(
                calendar_id="cal_abc123",
                title="Intro call",
                duration_minutes=45,
                buffer_minutes=10,
                window_days=30,
                min_notice_minutes=15,
                timezone="UTC",
                availability_constraints={"tue": {"start": "10:00", "end": "12:00"}},
                active=True,
            )
            assert page.duration_minutes == 45

    @respx.mock
    async def test_list(self) -> None:
        respx.get(f"{BASE}/v1/booking-pages").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            pager = await client.booking_pages.list()
            assert isinstance(pager, AsyncPager)
            assert len(pager.data) == 1

    @respx.mock
    async def test_get(self) -> None:
        respx.get(f"{BASE}/v1/booking-pages/bkp_abc123").mock(
            return_value=httpx.Response(200, json=BOOKING_PAGE_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            page = await client.booking_pages.get("bkp_abc123")
            assert page.id == "bkp_abc123"

    @respx.mock
    async def test_update(self) -> None:
        updated = {**BOOKING_PAGE_DATA, "title": "Renamed"}
        respx.patch(f"{BASE}/v1/booking-pages/bkp_abc123").mock(
            return_value=httpx.Response(200, json=updated)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            page = await client.booking_pages.update("bkp_abc123", title="Renamed", description="d")
            assert page.title == "Renamed"

    @respx.mock
    async def test_delete(self) -> None:
        respx.delete(f"{BASE}/v1/booking-pages/bkp_abc123").mock(
            return_value=httpx.Response(204)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            assert await client.booking_pages.delete("bkp_abc123") is None
