from __future__ import annotations

from datetime import datetime  # noqa: TCH003 — Pydantic needs this at runtime
from typing import Any, Literal

from pydantic import Field
from typing_extensions import NotRequired, Required, TypedDict

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource
from ..pagination import AsyncPager, ListResponse, SyncPager

ProposalStatus = Literal["pending", "confirmed", "expired", "cancelled"]
ProposalResponseAction = Literal["accept", "decline", "counter"]


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ProposalSlot(ChronaryModel):
    """A candidate time slot for a proposal."""

    id: str | None = None
    start_time: datetime
    end_time: datetime
    weight: float = 1.0
    calendar_id: str | None = None


class ProposalResponse(ChronaryModel):
    """An agent's response to a proposal."""

    id: str
    agent_id: str
    response: ProposalResponseAction
    selected_slot_id: str | None = None
    counter_slots: list[ProposalSlot] | None = None
    message: str | None = None
    created_at: datetime


class ProposalSummary(ChronaryModel):
    """A scheduling proposal (summary — no slots or responses)."""

    id: str
    title: str
    description: str | None = None
    organizer_agent_id: str
    participant_agent_ids: list[str]
    calendar_id: str
    status: ProposalStatus
    is_test: bool = False
    expires_at: datetime | None = None
    resolved_slot: ProposalSlot | None = None
    created_event_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class Proposal(ProposalSummary):
    """A full scheduling proposal with slots and responses."""

    slots: list[ProposalSlot] = Field(default_factory=list)
    responses: list[ProposalResponse] = Field(default_factory=list)


class ResolveProposalResponse(ChronaryModel):
    """Result of resolving a proposal."""

    status: Literal["confirmed", "cancelled"]
    resolved_slot: ProposalSlot | None = None
    reason: str | None = None


class CancelProposalResponse(ChronaryModel):
    """Result of cancelling a proposal."""

    status: Literal["cancelled"]


# ---------------------------------------------------------------------------
# Request param TypedDicts
# ---------------------------------------------------------------------------


class ProposalSlotParams(TypedDict):
    start_time: Required[str]
    end_time: Required[str]
    weight: NotRequired[float]
    calendar_id: NotRequired[str]


class ProposalCreateParams(TypedDict):
    title: Required[str]
    organizer_agent_id: Required[str]
    participant_agent_ids: Required[list[str]]
    calendar_id: Required[str]
    slots: Required[list[ProposalSlotParams]]
    description: NotRequired[str]
    expires_at: NotRequired[str]
    metadata: NotRequired[dict[str, Any]]


class ProposalRespondParams(TypedDict):
    agent_id: Required[str]
    response: Required[ProposalResponseAction]
    selected_slot_id: NotRequired[str]
    counter_slots: NotRequired[list[ProposalSlotParams]]
    message: NotRequired[str]


class ProposalListParams(TypedDict, total=False):
    status: ProposalStatus
    organizer_agent_id: str
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Sync resource
# ---------------------------------------------------------------------------

_PROPOSALS_PATH = "/v1/scheduling/proposals"


class Scheduling(SyncAPIResource):
    """client.scheduling — synchronous CRUD for scheduling proposals."""

    def create(
        self,
        *,
        title: str,
        organizer_agent_id: str,
        participant_agent_ids: list[str],
        calendar_id: str,
        slots: list[ProposalSlotParams],
        description: str | None = None,
        expires_at: str | None = None,
        metadata: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> ProposalSummary:
        body: dict[str, Any] = {
            "title": title,
            "organizer_agent_id": organizer_agent_id,
            "participant_agent_ids": participant_agent_ids,
            "calendar_id": calendar_id,
            "slots": slots,
        }
        if description is not None:
            body["description"] = description
        if expires_at is not None:
            body["expires_at"] = expires_at
        if metadata is not None:
            body["metadata"] = metadata
        resp = self._request("POST", _PROPOSALS_PATH, json=body, max_retries=max_retries)
        return self._build(ProposalSummary, resp)

    def list(
        self,
        *,
        status: ProposalStatus | None = None,
        organizer_agent_id: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> SyncPager[ProposalSummary]:
        params: dict[str, Any] = {
            "status": status,
            "organizer_agent_id": organizer_agent_id,
            "limit": limit,
            "offset": offset,
        }
        resp = self._request("GET", _PROPOSALS_PATH, params=params, max_retries=max_retries)
        raw = resp.json()
        list_resp = ListResponse[ProposalSummary](
            data=[ProposalSummary.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return SyncPager(
            list_resp,
            client=self._client,
            path=_PROPOSALS_PATH,
            params=params,
            model=ProposalSummary,
            request_id=resp.headers.get("X-Request-Id"),
        )

    def get(
        self,
        proposal_id: str,
        *,
        max_retries: int | None = None,
    ) -> Proposal:
        resp = self._request(
            "GET", f"{_PROPOSALS_PATH}/{proposal_id}", max_retries=max_retries
        )
        return self._build(Proposal, resp)

    def respond(
        self,
        proposal_id: str,
        *,
        agent_id: str,
        response: ProposalResponseAction,
        selected_slot_id: str | None = None,
        counter_slots: list[ProposalSlotParams] | None = None,
        message: str | None = None,
        max_retries: int | None = None,
    ) -> ProposalResponse:
        body: dict[str, Any] = {"agent_id": agent_id, "response": response}
        if selected_slot_id is not None:
            body["selected_slot_id"] = selected_slot_id
        if counter_slots is not None:
            body["counter_slots"] = counter_slots
        if message is not None:
            body["message"] = message
        path = f"{_PROPOSALS_PATH}/{proposal_id}/respond"
        resp = self._request("POST", path, json=body, max_retries=max_retries)
        return self._build(ProposalResponse, resp)

    def resolve(
        self,
        proposal_id: str,
        *,
        max_retries: int | None = None,
    ) -> ResolveProposalResponse:
        path = f"{_PROPOSALS_PATH}/{proposal_id}/resolve"
        resp = self._request("POST", path, max_retries=max_retries)
        return self._build(ResolveProposalResponse, resp)

    def cancel(
        self,
        proposal_id: str,
        *,
        max_retries: int | None = None,
    ) -> CancelProposalResponse:
        path = f"{_PROPOSALS_PATH}/{proposal_id}/cancel"
        resp = self._request("POST", path, max_retries=max_retries)
        return self._build(CancelProposalResponse, resp)


# ---------------------------------------------------------------------------
# Async resource
# ---------------------------------------------------------------------------


class AsyncScheduling(AsyncAPIResource):
    """client.scheduling — asynchronous CRUD for scheduling proposals."""

    async def create(
        self,
        *,
        title: str,
        organizer_agent_id: str,
        participant_agent_ids: list[str],
        calendar_id: str,
        slots: list[ProposalSlotParams],
        description: str | None = None,
        expires_at: str | None = None,
        metadata: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> ProposalSummary:
        body: dict[str, Any] = {
            "title": title,
            "organizer_agent_id": organizer_agent_id,
            "participant_agent_ids": participant_agent_ids,
            "calendar_id": calendar_id,
            "slots": slots,
        }
        if description is not None:
            body["description"] = description
        if expires_at is not None:
            body["expires_at"] = expires_at
        if metadata is not None:
            body["metadata"] = metadata
        resp = await self._request(
            "POST", _PROPOSALS_PATH, json=body, max_retries=max_retries
        )
        return self._build(ProposalSummary, resp)

    async def list(
        self,
        *,
        status: ProposalStatus | None = None,
        organizer_agent_id: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> AsyncPager[ProposalSummary]:
        params: dict[str, Any] = {
            "status": status,
            "organizer_agent_id": organizer_agent_id,
            "limit": limit,
            "offset": offset,
        }
        resp = await self._request(
            "GET", _PROPOSALS_PATH, params=params, max_retries=max_retries
        )
        raw = resp.json()
        list_resp = ListResponse[ProposalSummary](
            data=[ProposalSummary.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return AsyncPager(
            list_resp,
            client=self._client,
            path=_PROPOSALS_PATH,
            params=params,
            model=ProposalSummary,
            request_id=resp.headers.get("X-Request-Id"),
        )

    async def get(
        self,
        proposal_id: str,
        *,
        max_retries: int | None = None,
    ) -> Proposal:
        resp = await self._request(
            "GET", f"{_PROPOSALS_PATH}/{proposal_id}", max_retries=max_retries
        )
        return self._build(Proposal, resp)

    async def respond(
        self,
        proposal_id: str,
        *,
        agent_id: str,
        response: ProposalResponseAction,
        selected_slot_id: str | None = None,
        counter_slots: list[ProposalSlotParams] | None = None,
        message: str | None = None,
        max_retries: int | None = None,
    ) -> ProposalResponse:
        body: dict[str, Any] = {"agent_id": agent_id, "response": response}
        if selected_slot_id is not None:
            body["selected_slot_id"] = selected_slot_id
        if counter_slots is not None:
            body["counter_slots"] = counter_slots
        if message is not None:
            body["message"] = message
        path = f"{_PROPOSALS_PATH}/{proposal_id}/respond"
        resp = await self._request("POST", path, json=body, max_retries=max_retries)
        return self._build(ProposalResponse, resp)

    async def resolve(
        self,
        proposal_id: str,
        *,
        max_retries: int | None = None,
    ) -> ResolveProposalResponse:
        path = f"{_PROPOSALS_PATH}/{proposal_id}/resolve"
        resp = await self._request("POST", path, max_retries=max_retries)
        return self._build(ResolveProposalResponse, resp)

    async def cancel(
        self,
        proposal_id: str,
        *,
        max_retries: int | None = None,
    ) -> CancelProposalResponse:
        path = f"{_PROPOSALS_PATH}/{proposal_id}/cancel"
        resp = await self._request("POST", path, max_retries=max_retries)
        return self._build(CancelProposalResponse, resp)
