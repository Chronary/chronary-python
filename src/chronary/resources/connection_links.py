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


class ConnectionLinks(SyncAPIResource):
    def create(self, calendar_id: str, *, capabilities: list[Literal["availability", "publishing"]], publication_policy: Literal["none", "confirmed", "confirmed_tentative"] = "none", max_retries: int | None = None) -> ConnectionLink:
        resp = self._request("POST", f"/v1/calendars/{calendar_id}/connection-links", json={"capabilities": capabilities, "publication_policy": publication_policy}, max_retries=max_retries)
        return ConnectionLink.model_validate(resp.json())

    def get(self, link_id: str, *, max_retries: int | None = None) -> ConnectionLink:
        return ConnectionLink.model_validate(self._request("GET", f"/v1/connection-links/{link_id}", max_retries=max_retries).json())

    def cancel(self, link_id: str, *, max_retries: int | None = None) -> None:
        self._request("DELETE", f"/v1/connection-links/{link_id}", max_retries=max_retries)


class AsyncConnectionLinks(AsyncAPIResource):
    async def create(self, calendar_id: str, *, capabilities: list[Literal["availability", "publishing"]], publication_policy: Literal["none", "confirmed", "confirmed_tentative"] = "none", max_retries: int | None = None) -> ConnectionLink:
        resp = await self._request("POST", f"/v1/calendars/{calendar_id}/connection-links", json={"capabilities": capabilities, "publication_policy": publication_policy}, max_retries=max_retries)
        return ConnectionLink.model_validate(resp.json())

    async def get(self, link_id: str, *, max_retries: int | None = None) -> ConnectionLink:
        return ConnectionLink.model_validate((await self._request("GET", f"/v1/connection-links/{link_id}", max_retries=max_retries)).json())

    async def cancel(self, link_id: str, *, max_retries: int | None = None) -> None:
        await self._request("DELETE", f"/v1/connection-links/{link_id}", max_retries=max_retries)
