from __future__ import annotations

import json

import httpx
import respx

from chronary import AsyncChronary, Chronary
from chronary.resources.waitlist import WaitlistJoinResponse

BASE = "https://api.chronary.ai"
BODY = {
    "waitlisted": True,
    "message": "Thanks, you're on the list. We'll email you when your spot opens.",
}


class TestSyncWaitlist:
    @respx.mock
    def test_join_returns_generic_body(self) -> None:
        route = respx.post(f"{BASE}/v1/waitlist").mock(
            return_value=httpx.Response(202, json=BODY)
        )
        with Chronary(api_key=None, base_url=BASE) as client:
            result = client.waitlist.join(
                email="dev@acme.ai", tos_version="2026-01-01", intent="An agent"
            )
        assert isinstance(result, WaitlistJoinResponse)
        assert result.waitlisted is True
        assert result.message.startswith("Thanks")
        sent = json.loads(route.calls.last.request.content)
        assert sent == {"email": "dev@acme.ai", "tos_version": "2026-01-01", "intent": "An agent"}


class TestAsyncWaitlist:
    @respx.mock
    async def test_join(self) -> None:
        respx.post(f"{BASE}/v1/waitlist").mock(
            return_value=httpx.Response(202, json=BODY)
        )
        async with AsyncChronary(api_key=None, base_url=BASE) as client:
            result = await client.waitlist.join(email="dev@acme.ai")
        assert result.waitlisted is True
