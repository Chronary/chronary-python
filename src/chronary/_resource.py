from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from ._models import ChronaryModel

if TYPE_CHECKING:
    import httpx

    from ._base_client import AsyncAPIClient, SyncAPIClient

_T = TypeVar("_T", bound=ChronaryModel)


class SyncAPIResource:
    """Base class for synchronous API resource namespaces."""

    _client: SyncAPIClient

    def __init__(self, client: SyncAPIClient) -> None:
        self._client = client

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> httpx.Response:
        return self._client._request(
            method, path, json=json, params=params, max_retries=max_retries
        )

    def _build(self, model_cls: type[_T], response: httpx.Response) -> _T:
        """Validate response JSON into *model_cls* and attach X-Request-Id."""
        obj = model_cls.model_validate(response.json())
        request_id = response.headers.get("X-Request-Id")
        if request_id is not None:
            object.__setattr__(obj, "_request_id", request_id)
        return obj


class AsyncAPIResource:
    """Base class for asynchronous API resource namespaces."""

    _client: AsyncAPIClient

    def __init__(self, client: AsyncAPIClient) -> None:
        self._client = client

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> httpx.Response:
        return await self._client._request(
            method, path, json=json, params=params, max_retries=max_retries
        )

    def _build(self, model_cls: type[_T], response: httpx.Response) -> _T:
        """Validate response JSON into *model_cls* and attach X-Request-Id."""
        obj = model_cls.model_validate(response.json())
        request_id = response.headers.get("X-Request-Id")
        if request_id is not None:
            object.__setattr__(obj, "_request_id", request_id)
        return obj
