from __future__ import annotations

import httpx
import respx

from chronary import AcceptedTerms, AsyncChronary, Chronary

BASE = "https://api.chronary.ai"

ACCEPTED_DATA = {
    "accepted_terms_version": "2026-06-01",
    "accepted_terms_at": "2026-06-06T16:20:00Z",
}


class TestSyncTerms:
    @respx.mock
    def test_accept(self) -> None:
        route = respx.post(f"{BASE}/v1/terms/accept").mock(
            return_value=httpx.Response(200, json=ACCEPTED_DATA)
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            accepted = client.terms.accept(tos_version="2026-06-01")
            assert isinstance(accepted, AcceptedTerms)
            assert accepted.accepted_terms_version == "2026-06-01"
            assert route.calls.last.request.read() == b'{"tos_version":"2026-06-01"}'

    @respx.mock
    def test_accept_request_id(self) -> None:
        respx.post(f"{BASE}/v1/terms/accept").mock(
            return_value=httpx.Response(
                200,
                json=ACCEPTED_DATA,
                headers={"X-Request-Id": "req_terms_accept_1"},
            )
        )
        with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
            accepted = client.terms.accept(tos_version="2026-06-01")
            assert accepted._request_id == "req_terms_accept_1"


class TestAsyncTerms:
    @respx.mock
    async def test_accept(self) -> None:
        respx.post(f"{BASE}/v1/terms/accept").mock(
            return_value=httpx.Response(200, json=ACCEPTED_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
            accepted = await client.terms.accept(tos_version="2026-06-01")
            assert isinstance(accepted, AcceptedTerms)
            assert accepted.accepted_terms_version == "2026-06-01"
