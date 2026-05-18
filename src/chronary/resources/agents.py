from __future__ import annotations

from datetime import datetime  # noqa: TCH003 — Pydantic needs this at runtime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field
from typing_extensions import NotRequired, Required, TypedDict

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource
from ..pagination import AsyncPager, ListResponse, SyncPager
from .availability import AsyncAvailability, Availability
from .calendars import AgentCalendars, AsyncAgentCalendars
from .events import AgentEvents, AsyncAgentEvents

if TYPE_CHECKING:
    from .._base_client import AsyncAPIClient, SyncAPIClient

# Sentinel for distinguishing "not passed" from "explicitly passed None"
_UNSET: Any = object()


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------


class Agent(ChronaryModel):
    """An agent registered with the Chronary API."""

    id: str
    name: str
    type: Literal["ai", "human", "resource"]
    description: str | None = None
    status: Literal["active", "paused", "decommissioned"]
    metadata: dict[str, Any]
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


# ---------------------------------------------------------------------------
# Request param TypedDicts
# ---------------------------------------------------------------------------


class AgentCreateParams(TypedDict):
    name: Required[str]
    type: Required[Literal["ai", "human", "resource"]]
    description: NotRequired[str]
    metadata: NotRequired[dict[str, Any]]


class AgentUpdateParams(TypedDict, total=False):
    name: str
    description: str | None
    status: Literal["active", "paused"]
    metadata: dict[str, Any]


class AgentListParams(TypedDict, total=False):
    type: Literal["ai", "human", "resource"]
    status: Literal["active", "paused", "decommissioned"]
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Sync resource
# ---------------------------------------------------------------------------

_AGENTS_PATH = "/v1/agents"


class Agents(SyncAPIResource):
    """client.agents — synchronous CRUD for agent resources."""

    _calendars: AgentCalendars | None
    _events: AgentEvents | None
    _availability: Availability | None

    def __init__(self, client: SyncAPIClient) -> None:  # type: ignore[override]
        super().__init__(client)
        self._calendars = None
        self._events = None
        self._availability = None

    @property
    def calendars(self) -> AgentCalendars:
        if self._calendars is None:
            self._calendars = AgentCalendars(self._client)
        return self._calendars

    @property
    def events(self) -> AgentEvents:
        if self._events is None:
            self._events = AgentEvents(self._client)
        return self._events

    @property
    def availability(self) -> Availability:
        if self._availability is None:
            self._availability = Availability(self._client)
        return self._availability

    def create(
        self,
        *,
        name: str,
        type: Literal["ai", "human", "resource"],
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> Agent:
        """Register your agent with Chronary.

        Creates a Chronary identity for an agent that already exists in your system,
        so it can own calendars, events, and webhooks.
        """
        body: dict[str, Any] = {"name": name, "type": type}
        if description is not None:
            body["description"] = description
        if metadata is not None:
            body["metadata"] = metadata
        resp = self._request("POST", _AGENTS_PATH, json=body, max_retries=max_retries)
        return self._build(Agent, resp)

    def list(
        self,
        *,
        type: Literal["ai", "human", "resource"] | None = None,
        status: Literal["active", "paused", "decommissioned"] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> SyncPager[Agent]:
        params: dict[str, Any] = {
            "type": type,
            "status": status,
            "limit": limit,
            "offset": offset,
        }
        resp = self._request("GET", _AGENTS_PATH, params=params, max_retries=max_retries)
        raw = resp.json()
        list_resp = ListResponse[Agent](
            data=[Agent.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return SyncPager(
            list_resp,
            client=self._client,
            path=_AGENTS_PATH,
            params=params,
            model=Agent,
            request_id=resp.headers.get("X-Request-Id"),
        )

    def get(
        self,
        agent_id: str,
        *,
        max_retries: int | None = None,
    ) -> Agent:
        resp = self._request("GET", f"{_AGENTS_PATH}/{agent_id}", max_retries=max_retries)
        return self._build(Agent, resp)

    def update(
        self,
        agent_id: str,
        *,
        name: str | None = None,
        description: str | None = _UNSET,  # type: ignore[assignment]
        status: Literal["active", "paused"] | None = None,
        metadata: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> Agent:
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not _UNSET:
            body["description"] = description
        if status is not None:
            body["status"] = status
        if metadata is not None:
            body["metadata"] = metadata
        resp = self._request(
            "PATCH", f"{_AGENTS_PATH}/{agent_id}", json=body, max_retries=max_retries
        )
        return self._build(Agent, resp)

    def delete(
        self,
        agent_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        self._request("DELETE", f"{_AGENTS_PATH}/{agent_id}", max_retries=max_retries)


# ---------------------------------------------------------------------------
# Async resource
# ---------------------------------------------------------------------------


class AsyncAgents(AsyncAPIResource):
    """client.agents — asynchronous CRUD for agent resources."""

    _calendars: AsyncAgentCalendars | None
    _events: AsyncAgentEvents | None
    _availability: AsyncAvailability | None

    def __init__(self, client: AsyncAPIClient) -> None:  # type: ignore[override]
        super().__init__(client)
        self._calendars = None
        self._events = None
        self._availability = None

    @property
    def calendars(self) -> AsyncAgentCalendars:
        if self._calendars is None:
            self._calendars = AsyncAgentCalendars(self._client)
        return self._calendars

    @property
    def events(self) -> AsyncAgentEvents:
        if self._events is None:
            self._events = AsyncAgentEvents(self._client)
        return self._events

    @property
    def availability(self) -> AsyncAvailability:
        if self._availability is None:
            self._availability = AsyncAvailability(self._client)
        return self._availability

    async def create(
        self,
        *,
        name: str,
        type: Literal["ai", "human", "resource"],
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> Agent:
        """Register your agent with Chronary.

        Creates a Chronary identity for an agent that already exists in your system,
        so it can own calendars, events, and webhooks.
        """
        body: dict[str, Any] = {"name": name, "type": type}
        if description is not None:
            body["description"] = description
        if metadata is not None:
            body["metadata"] = metadata
        resp = await self._request(
            "POST", _AGENTS_PATH, json=body, max_retries=max_retries
        )
        return self._build(Agent, resp)

    async def list(
        self,
        *,
        type: Literal["ai", "human", "resource"] | None = None,
        status: Literal["active", "paused", "decommissioned"] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        max_retries: int | None = None,
    ) -> AsyncPager[Agent]:
        params: dict[str, Any] = {
            "type": type,
            "status": status,
            "limit": limit,
            "offset": offset,
        }
        resp = await self._request(
            "GET", _AGENTS_PATH, params=params, max_retries=max_retries
        )
        raw = resp.json()
        list_resp = ListResponse[Agent](
            data=[Agent.model_validate(item) for item in raw["data"]],
            total=raw["total"],
            limit=raw["limit"],
            offset=raw["offset"],
        )
        return AsyncPager(
            list_resp,
            client=self._client,
            path=_AGENTS_PATH,
            params=params,
            model=Agent,
            request_id=resp.headers.get("X-Request-Id"),
        )

    async def get(
        self,
        agent_id: str,
        *,
        max_retries: int | None = None,
    ) -> Agent:
        resp = await self._request(
            "GET", f"{_AGENTS_PATH}/{agent_id}", max_retries=max_retries
        )
        return self._build(Agent, resp)

    async def update(
        self,
        agent_id: str,
        *,
        name: str | None = None,
        description: str | None = _UNSET,  # type: ignore[assignment]
        status: Literal["active", "paused"] | None = None,
        metadata: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> Agent:
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not _UNSET:
            body["description"] = description
        if status is not None:
            body["status"] = status
        if metadata is not None:
            body["metadata"] = metadata
        resp = await self._request(
            "PATCH", f"{_AGENTS_PATH}/{agent_id}", json=body, max_retries=max_retries
        )
        return self._build(Agent, resp)

    async def delete(
        self,
        agent_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        await self._request(
            "DELETE", f"{_AGENTS_PATH}/{agent_id}", max_retries=max_retries
        )
