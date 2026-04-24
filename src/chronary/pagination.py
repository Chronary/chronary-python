from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from ._models import ChronaryModel

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from ._base_client import AsyncAPIClient, SyncAPIClient

T = TypeVar("T", bound=ChronaryModel)


class ListResponse(ChronaryModel, Generic[T]):
    """Paginated list response wrapping the API's { data, total, limit, offset } envelope."""

    data: list[T]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + self.limit < self.total


class SyncPager(Generic[T]):
    """Wraps a ListResponse and provides auto-paging iteration."""

    _response: ListResponse[T]
    _client: SyncAPIClient
    _path: str
    _params: dict[str, Any]
    _model: type[T]
    _request_id: str | None

    def __init__(
        self,
        response: ListResponse[T],
        *,
        client: SyncAPIClient,
        path: str,
        params: dict[str, Any],
        model: type[T],
        request_id: str | None = None,
    ) -> None:
        self._response = response
        self._client = client
        self._path = path
        self._params = params
        self._model = model
        self._request_id = request_id

    @property
    def data(self) -> list[T]:
        return self._response.data

    @property
    def total(self) -> int:
        return self._response.total

    @property
    def limit(self) -> int:
        return self._response.limit

    @property
    def offset(self) -> int:
        return self._response.offset

    @property
    def has_more(self) -> bool:
        return self._response.has_more

    def auto_paging_iter(self) -> Iterator[T]:
        page = self._response
        while True:
            yield from page.data
            if not page.has_more:
                break
            next_offset = page.offset + page.limit
            params = {**self._params, "offset": next_offset, "limit": page.limit}
            resp = self._client._request("GET", self._path, params=params)
            self._request_id = resp.headers.get("X-Request-Id")
            raw = resp.json()
            page = ListResponse[self._model](  # type: ignore[valid-type]
                data=[self._model.model_validate(item) for item in raw["data"]],
                total=raw["total"],
                limit=raw["limit"],
                offset=raw["offset"],
            )


class AsyncPager(Generic[T]):
    """Wraps a ListResponse and provides async auto-paging iteration."""

    _response: ListResponse[T]
    _client: AsyncAPIClient
    _path: str
    _params: dict[str, Any]
    _model: type[T]
    _request_id: str | None

    def __init__(
        self,
        response: ListResponse[T],
        *,
        client: AsyncAPIClient,
        path: str,
        params: dict[str, Any],
        model: type[T],
        request_id: str | None = None,
    ) -> None:
        self._response = response
        self._client = client
        self._path = path
        self._params = params
        self._model = model
        self._request_id = request_id

    @property
    def data(self) -> list[T]:
        return self._response.data

    @property
    def total(self) -> int:
        return self._response.total

    @property
    def limit(self) -> int:
        return self._response.limit

    @property
    def offset(self) -> int:
        return self._response.offset

    @property
    def has_more(self) -> bool:
        return self._response.has_more

    async def auto_paging_iter(self) -> AsyncIterator[T]:
        page = self._response
        while True:
            for item in page.data:
                yield item
            if not page.has_more:
                break
            next_offset = page.offset + page.limit
            params = {**self._params, "offset": next_offset, "limit": page.limit}
            resp = await self._client._request("GET", self._path, params=params)
            self._request_id = resp.headers.get("X-Request-Id")
            raw = resp.json()
            page = ListResponse[self._model](  # type: ignore[valid-type]
                data=[self._model.model_validate(item) for item in raw["data"]],
                total=raw["total"],
                limit=raw["limit"],
                offset=raw["offset"],
            )
