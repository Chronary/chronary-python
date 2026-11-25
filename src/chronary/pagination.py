from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from ._exceptions import APIError
from ._models import ChronaryModel

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from ._base_client import AsyncAPIClient, SyncAPIClient

T = TypeVar("T", bound=ChronaryModel)


class ListResponse(ChronaryModel, Generic[T]):
    """Paginated list response wrapping the API's { data, total, limit, offset } envelope.

    Lists that have cursors (agents, calendars, the org-wide events list) also
    carry ``next_cursor``: pass it as ``cursor`` for the next page; ``None`` on
    the last page. It stays ``None`` on lists that page by offset only.
    """

    data: list[T]
    total: int
    limit: int
    offset: int
    next_cursor: str | None = None

    @property
    def cursor_paged(self) -> bool:
        """True when the list returned ``next_cursor`` (so it pages by cursor)."""
        return "next_cursor" in self.model_fields_set

    @property
    def has_more(self) -> bool:
        if self.cursor_paged:
            return self.next_cursor is not None
        return self.offset + self.limit < self.total


def parse_list_response(model: type[T], raw: dict[str, Any]) -> ListResponse[T]:
    """Build a ``ListResponse`` from a list body, keeping ``next_cursor`` when present."""
    extra: dict[str, Any] = {}
    if "next_cursor" in raw:
        extra["next_cursor"] = raw["next_cursor"]
    return ListResponse[model](  # type: ignore[valid-type]
        data=[model.model_validate(item) for item in raw["data"]],
        total=raw["total"],
        limit=raw["limit"],
        offset=raw["offset"],
        **extra,
    )


def _next_page_params(params: dict[str, Any], page: ListResponse[Any]) -> dict[str, Any]:
    """Query for the page after ``page``: by ``next_cursor`` where the list has
    one (#2691: not limited by the API's 10,000-row offset cap; a cursor is
    sent without an offset, which the API refuses to combine), else by offset."""
    if page.cursor_paged:
        # The cursor just sent coming back would page forever.
        if page.next_cursor == params.get("cursor"):
            raise APIError("The API returned the same next_cursor twice; stopping.")
        return {**params, "cursor": page.next_cursor, "offset": None, "limit": page.limit}
    return {**params, "offset": page.offset + page.limit, "limit": page.limit}


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

    @property
    def next_cursor(self) -> str | None:
        """Pass as ``cursor`` to the same list for the next page (cursor lists only)."""
        return self._response.next_cursor

    def auto_paging_iter(self) -> Iterator[T]:
        page = self._response
        params = self._params
        while True:
            yield from page.data
            if not page.has_more or not page.data:
                break
            params = _next_page_params(params, page)
            resp = self._client._request("GET", self._path, params=params)
            self._request_id = resp.headers.get("X-Request-Id")
            page = parse_list_response(self._model, resp.json())


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

    @property
    def next_cursor(self) -> str | None:
        """Pass as ``cursor`` to the same list for the next page (cursor lists only)."""
        return self._response.next_cursor

    async def auto_paging_iter(self) -> AsyncIterator[T]:
        page = self._response
        params = self._params
        while True:
            for item in page.data:
                yield item
            if not page.has_more or not page.data:
                break
            params = _next_page_params(params, page)
            resp = await self._client._request("GET", self._path, params=params)
            self._request_id = resp.headers.get("X-Request-Id")
            page = parse_list_response(self._model, resp.json())
