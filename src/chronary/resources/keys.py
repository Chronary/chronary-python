from __future__ import annotations

from datetime import datetime  # noqa: TCH003 -- Pydantic needs this at runtime
from typing import Any, Literal

from typing_extensions import NotRequired, Required, TypedDict

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource


class ScopedApiKey(ChronaryModel):
    """An agent-scoped API key."""

    id: str
    mode: Literal["live", "test"]
    key_prefix: str
    agent_id: str
    label: str | None = None
    created_at: datetime


class CreatedScopedApiKey(ScopedApiKey):
    """An agent-scoped API key including the one-time secret."""

    key: str


class ScopedApiKeyCreateParams(TypedDict):
    agent_id: Required[str]
    mode: Required[Literal["live", "test"]]
    label: NotRequired[str]


_KEYS_PATH = "/v1/keys"


class Keys(SyncAPIResource):
    """client.keys -- synchronous agent-scoped API key operations."""

    def create(
        self,
        *,
        agent_id: str,
        mode: Literal["live", "test"],
        label: str | None = None,
        max_retries: int | None = None,
    ) -> CreatedScopedApiKey:
        body: dict[str, Any] = {"agent_id": agent_id, "mode": mode}
        if label is not None:
            body["label"] = label
        resp = self._request("POST", _KEYS_PATH, json=body, max_retries=max_retries)
        return self._build(CreatedScopedApiKey, resp)

    def list(
        self,
        *,
        max_retries: int | None = None,
    ) -> list[ScopedApiKey]:
        resp = self._request("GET", _KEYS_PATH, max_retries=max_retries)
        raw = resp.json()
        request_id = resp.headers.get("X-Request-Id")
        return [self._build_from_item(item, request_id) for item in raw["keys"]]

    def delete(
        self,
        key_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        self._request("DELETE", f"{_KEYS_PATH}/{key_id}", max_retries=max_retries)

    @staticmethod
    def _build_from_item(
        item: dict[str, Any],
        request_id: str | None,
    ) -> ScopedApiKey:
        obj = ScopedApiKey.model_validate(item)
        if request_id is not None:
            object.__setattr__(obj, "_request_id", request_id)
        return obj


class AsyncKeys(AsyncAPIResource):
    """client.keys -- asynchronous agent-scoped API key operations."""

    async def create(
        self,
        *,
        agent_id: str,
        mode: Literal["live", "test"],
        label: str | None = None,
        max_retries: int | None = None,
    ) -> CreatedScopedApiKey:
        body: dict[str, Any] = {"agent_id": agent_id, "mode": mode}
        if label is not None:
            body["label"] = label
        resp = await self._request(
            "POST",
            _KEYS_PATH,
            json=body,
            max_retries=max_retries,
        )
        return self._build(CreatedScopedApiKey, resp)

    async def list(
        self,
        *,
        max_retries: int | None = None,
    ) -> list[ScopedApiKey]:
        resp = await self._request("GET", _KEYS_PATH, max_retries=max_retries)
        raw = resp.json()
        request_id = resp.headers.get("X-Request-Id")
        return [Keys._build_from_item(item, request_id) for item in raw["keys"]]

    async def delete(
        self,
        key_id: str,
        *,
        max_retries: int | None = None,
    ) -> None:
        await self._request("DELETE", f"{_KEYS_PATH}/{key_id}", max_retries=max_retries)
