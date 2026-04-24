from __future__ import annotations

import httpx
import respx

from chronary import AsyncChronary, Chronary, FeedbackAcceptedResponse

BASE = "https://api.chronary.ai"

ACCEPTED = {"status": "accepted"}


class TestSyncFeedback:
    @respx.mock
    def test_submit_bug(self) -> None:
        route = respx.post(f"{BASE}/v1/feedback").mock(
            return_value=httpx.Response(202, json=ACCEPTED)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            result = client.feedback.submit(
                type="bug",
                message="Availability endpoint returns empty for UTC+13.",
            )
            assert isinstance(result, FeedbackAcceptedResponse)
            assert result.status == "accepted"
        assert route.called
        sent = route.calls.last.request.content.decode()
        assert '"type": "bug"' in sent or '"type":"bug"' in sent

    @respx.mock
    def test_submit_with_context(self) -> None:
        route = respx.post(f"{BASE}/v1/feedback").mock(
            return_value=httpx.Response(202, json=ACCEPTED)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            client.feedback.submit(
                type="feature",
                message="Expose a batch-create events endpoint please.",
                context={"sdk_name": "chronary-python", "sdk_version": "0.4.2"},
            )
        sent = route.calls.last.request.content.decode()
        assert "sdk_name" in sent
        assert "chronary-python" in sent


class TestAsyncFeedback:
    @respx.mock
    async def test_submit(self) -> None:
        route = respx.post(f"{BASE}/v1/feedback").mock(
            return_value=httpx.Response(202, json=ACCEPTED)
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            result = await client.feedback.submit(
                type="friction",
                message="Friction submitting proposals when organizer is scoped key.",
            )
            assert result.status == "accepted"
        assert route.called
