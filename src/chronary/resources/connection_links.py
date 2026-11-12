from __future__ import annotations

from typing import Any, Literal

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource


class ConnectionLink(ChronaryModel):
    id: str
    calendar_id: str
    setup_url: str | None = None
    status: Literal["awaiting_human", "in_progress", "completed", "declined", "expired", "cancelled"]
    expires_at: str
    connection_id: str | None = None
    reused: bool | None = None
    requesting_agent_id: str | None = None
    requested_capabilities: list[Literal["availability", "publishing"]] | None = None
    requested_publication_policy: Literal["confirmed", "confirmed_tentative"] | None = None
    created_at: str | None = None


ConnectionLinkStatus = Literal["awaiting_human", "in_progress", "completed", "declined", "expired", "cancelled"]


def _list_params(status: ConnectionLinkStatus | None, calendar_id: str | None, limit: int | None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if status is not None:
        params["status"] = status
    if calendar_id is not None:
        params["calendar_id"] = calendar_id
    if limit is not None:
        params["limit"] = limit
    return params


class ConnectionLinks(SyncAPIResource):
    def create(self, calendar_id: str, *, capabilities: list[Literal["availability", "publishing"]], publication_policy: Literal["none", "confirmed", "confirmed_tentative"] = "none", max_retries: int | None = None) -> ConnectionLink:
        resp = self._request("POST", f"/v1/calendars/{calendar_id}/connection-links", json={"capabilities": capabilities, "publication_policy": publication_policy}, max_retries=max_retries)
        return ConnectionLink.model_validate(resp.json())

    def list(self, *, status: ConnectionLinkStatus | None = None, calendar_id: str | None = None, limit: int | None = None, max_retries: int | None = None) -> list[ConnectionLink]:
        """Setup links, newest first. An agent-scoped key sees only its own calendars' links."""
        resp = self._request("GET", "/v1/connection-links", params=_list_params(status, calendar_id, limit), max_retries=max_retries)
        return [ConnectionLink.model_validate(item) for item in resp.json()["data"]]

    def get(self, link_id: str, *, max_retries: int | None = None) -> ConnectionLink:
        return ConnectionLink.model_validate(self._request("GET", f"/v1/connection-links/{link_id}", max_retries=max_retries).json())

    def cancel(self, link_id: str, *, max_retries: int | None = None) -> None:
        self._request("DELETE", f"/v1/connection-links/{link_id}", max_retries=max_retries)


class AsyncConnectionLinks(AsyncAPIResource):
    async def create(self, calendar_id: str, *, capabilities: list[Literal["availability", "publishing"]], publication_policy: Literal["none", "confirmed", "confirmed_tentative"] = "none", max_retries: int | None = None) -> ConnectionLink:
        resp = await self._request("POST", f"/v1/calendars/{calendar_id}/connection-links", json={"capabilities": capabilities, "publication_policy": publication_policy}, max_retries=max_retries)
        return ConnectionLink.model_validate(resp.json())

    async def list(self, *, status: ConnectionLinkStatus | None = None, calendar_id: str | None = None, limit: int | None = None, max_retries: int | None = None) -> list[ConnectionLink]:
        """Setup links, newest first. An agent-scoped key sees only its own calendars' links."""
        resp = await self._request("GET", "/v1/connection-links", params=_list_params(status, calendar_id, limit), max_retries=max_retries)
        return [ConnectionLink.model_validate(item) for item in resp.json()["data"]]

    async def get(self, link_id: str, *, max_retries: int | None = None) -> ConnectionLink:
        return ConnectionLink.model_validate((await self._request("GET", f"/v1/connection-links/{link_id}", max_retries=max_retries)).json())

    async def cancel(self, link_id: str, *, max_retries: int | None = None) -> None:
        await self._request("DELETE", f"/v1/connection-links/{link_id}", max_retries=max_retries)
