from __future__ import annotations

import httpx
import respx

from chronary import (
    AsyncChronary,
    CancelProposalResponse,
    Chronary,
    Proposal,
    ProposalResponse,
    ProposalSummary,
    ResolveProposalResponse,
)
from chronary.pagination import AsyncPager, SyncPager

BASE = "https://api.chronary.ai"

PROPOSAL_SUMMARY_DATA = {
    "id": "spr_abc123",
    "title": "Project sync",
    "description": None,
    "organizer_agent_id": "agt_org",
    "participant_agent_ids": ["agt_a", "agt_b"],
    "calendar_id": "cal_team",
    "status": "pending",
    "is_test": False,
    "expires_at": None,
    "resolved_slot": None,
    "created_event_id": None,
    "metadata": {},
    "created_at": "2026-04-16T12:00:00Z",
    "updated_at": "2026-04-16T12:00:00Z",
}

PROPOSAL_FULL_DATA = {
    **PROPOSAL_SUMMARY_DATA,
    "slots": [
        {
            "id": "slt_1",
            "start_time": "2026-04-20T14:00:00Z",
            "end_time": "2026-04-20T15:00:00Z",
            "weight": 1.0,
            "calendar_id": None,
        }
    ],
    "responses": [],
}

RESPONSE_DATA = {
    "id": "rsp_1",
    "agent_id": "agt_a",
    "response": "accept",
    "selected_slot_id": "slt_1",
    "counter_slots": None,
    "message": None,
    "created_at": "2026-04-16T13:00:00Z",
}

LIST_RESPONSE = {
    "data": [PROPOSAL_SUMMARY_DATA],
    "total": 1,
    "limit": 50,
    "offset": 0,
}


class TestSyncScheduling:
    @respx.mock
    def test_create(self) -> None:
        respx.post(f"{BASE}/v1/scheduling/proposals").mock(
            return_value=httpx.Response(201, json=PROPOSAL_SUMMARY_DATA)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            proposal = client.scheduling.create(
                title="Project sync",
                organizer_agent_id="agt_org",
                participant_agent_ids=["agt_a", "agt_b"],
                calendar_id="cal_team",
                slots=[{"start_time": "2026-04-20T14:00:00Z", "end_time": "2026-04-20T15:00:00Z"}],
            )
            assert isinstance(proposal, ProposalSummary)
            assert proposal.id == "spr_abc123"

    @respx.mock
    def test_list(self) -> None:
        respx.get(f"{BASE}/v1/scheduling/proposals").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            pager = client.scheduling.list()
            assert isinstance(pager, SyncPager)
            assert len(pager.data) == 1
            assert pager.data[0].id == "spr_abc123"

    @respx.mock
    def test_get(self) -> None:
        respx.get(f"{BASE}/v1/scheduling/proposals/spr_abc123").mock(
            return_value=httpx.Response(200, json=PROPOSAL_FULL_DATA)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            proposal = client.scheduling.get("spr_abc123")
            assert isinstance(proposal, Proposal)
            assert len(proposal.slots) == 1
            assert proposal.responses == []

    @respx.mock
    def test_respond(self) -> None:
        respx.post(f"{BASE}/v1/scheduling/proposals/spr_abc123/respond").mock(
            return_value=httpx.Response(200, json=RESPONSE_DATA)
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            resp = client.scheduling.respond(
                "spr_abc123",
                agent_id="agt_a",
                response="accept",
                selected_slot_id="slt_1",
            )
            assert isinstance(resp, ProposalResponse)
            assert resp.response == "accept"

    @respx.mock
    def test_resolve(self) -> None:
        respx.post(f"{BASE}/v1/scheduling/proposals/spr_abc123/resolve").mock(
            return_value=httpx.Response(
                200,
                json={
                    "status": "confirmed",
                    "resolved_slot": {
                        "id": "slt_1",
                        "start_time": "2026-04-20T14:00:00Z",
                        "end_time": "2026-04-20T15:00:00Z",
                        "weight": 1.0,
                        "calendar_id": None,
                    },
                },
            )
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            result = client.scheduling.resolve("spr_abc123")
            assert isinstance(result, ResolveProposalResponse)
            assert result.status == "confirmed"
            assert result.resolved_slot is not None

    @respx.mock
    def test_cancel(self) -> None:
        respx.post(f"{BASE}/v1/scheduling/proposals/spr_abc123/cancel").mock(
            return_value=httpx.Response(200, json={"status": "cancelled"})
        )
        with Chronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            result = client.scheduling.cancel("spr_abc123")
            assert isinstance(result, CancelProposalResponse)
            assert result.status == "cancelled"


class TestAsyncScheduling:
    @respx.mock
    async def test_create(self) -> None:
        respx.post(f"{BASE}/v1/scheduling/proposals").mock(
            return_value=httpx.Response(201, json=PROPOSAL_SUMMARY_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            proposal = await client.scheduling.create(
                title="Project sync",
                organizer_agent_id="agt_org",
                participant_agent_ids=["agt_a", "agt_b"],
                calendar_id="cal_team",
                slots=[{"start_time": "2026-04-20T14:00:00Z", "end_time": "2026-04-20T15:00:00Z"}],
            )
            assert proposal.id == "spr_abc123"

    @respx.mock
    async def test_list(self) -> None:
        respx.get(f"{BASE}/v1/scheduling/proposals").mock(
            return_value=httpx.Response(200, json=LIST_RESPONSE)
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            pager = await client.scheduling.list()
            assert isinstance(pager, AsyncPager)

    @respx.mock
    async def test_respond(self) -> None:
        respx.post(f"{BASE}/v1/scheduling/proposals/spr_abc123/respond").mock(
            return_value=httpx.Response(200, json=RESPONSE_DATA)
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            resp = await client.scheduling.respond(
                "spr_abc123",
                agent_id="agt_a",
                response="accept",
                selected_slot_id="slt_1",
            )
            assert resp.response == "accept"

    @respx.mock
    async def test_cancel(self) -> None:
        respx.post(f"{BASE}/v1/scheduling/proposals/spr_abc123/cancel").mock(
            return_value=httpx.Response(200, json={"status": "cancelled"})
        )
        async with AsyncChronary(api_key="chr_sk_test_x", base_url=BASE) as client:
            result = await client.scheduling.cancel("spr_abc123")
            assert result.status == "cancelled"
