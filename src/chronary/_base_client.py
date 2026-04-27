from __future__ import annotations

import os
import random
import time
from typing import Any, Literal

import httpx

KeyType = Literal["backend", "agent"]

from ._exceptions import (
    APIConnectionError,
    APITimeoutError,
    _make_status_error,
)
from ._version import __version__

_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
_BACKOFF_BASE = 0.5
_BACKOFF_MAX = 8.0
_JITTER_FACTOR = 0.25
_IDEMPOTENCY_HEADER = "Idempotency-Key"


def _default_headers(api_key: str | None) -> dict[str, str]:
    # api_key is optional — some endpoints (plans.list, agent_auth.sign_up) do
    # not require auth. When a caller invokes an authed endpoint without a key,
    # the server returns 401 and the SDK surfaces it as AuthenticationError —
    # same error shape as if the key were explicitly wrong.
    headers = {
        "User-Agent": f"chronary-python/{__version__}",
        "Accept": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _sleep_time(attempt: int, retry_after: str | None) -> float:
    """Calculate sleep duration with exponential backoff and jitter."""
    if retry_after is not None:
        try:
            return float(retry_after)
        except ValueError:
            pass
    delay = min(_BACKOFF_BASE * (2**attempt), _BACKOFF_MAX)
    jitter = delay * _JITTER_FACTOR * random.random()  # noqa: S311
    return delay + jitter


def _resolve_credentials(
    api_key: str | None, agent_key: str | None
) -> tuple[str | None, KeyType | None]:
    """Resolve auth credentials from kwargs or env vars.

    Kwarg takes precedence over env. Raises TypeError if both kwargs are
    explicitly set (mutual exclusion). If neither kwarg is set but both env
    vars are populated, ``CHRONARY_API_KEY`` wins deterministically — callers
    who want the agent key should pass ``agent_key=`` explicitly or unset
    the backend env var.

    Returns ``(token, key_type)``; either or both may be None if no
    credential is available. Unauthenticated clients are supported —
    ``plans.list`` and ``agent_auth.sign_up`` require no auth.
    """
    if api_key is not None and agent_key is not None:
        raise TypeError(
            "Pass either api_key= or agent_key=, not both. "
            "api_key accepts org-level keys (chr_sk_*); agent_key accepts "
            "agent-scoped keys (chr_ak_*)."
        )
    if api_key is not None:
        return api_key, "backend"
    if agent_key is not None:
        return agent_key, "agent"

    env_api = os.environ.get("CHRONARY_API_KEY")
    if env_api:
        return env_api, "backend"
    env_agent = os.environ.get("CHRONARY_AGENT_KEY")
    if env_agent:
        return env_agent, "agent"

    return None, None


class SyncAPIClient:
    """Synchronous HTTP client for the Chronary API."""

    _client: httpx.Client
    _owns_client: bool
    _api_key: str | None
    _key_type: KeyType | None
    base_url: str
    max_retries: int

    def __init__(
        self,
        *,
        api_key: str | None = None,
        agent_key: str | None = None,
        base_url: str = "https://api.chronary.ai",
        timeout: float = 60.0,
        max_retries: int = 2,
        httpx_client: httpx.Client | None = None,
    ) -> None:
        self._api_key, self._key_type = _resolve_credentials(api_key, agent_key)
        self.base_url = base_url
        self.max_retries = max_retries

        if httpx_client is not None:
            self._client = httpx_client
            self._owns_client = False
        else:
            self._client = httpx.Client(
                base_url=base_url,
                headers=_default_headers(self._api_key),
                timeout=timeout,
            )
            self._owns_client = True

    @property
    def key_type(self) -> KeyType | None:
        """Which credential the client is using — ``"backend"``, ``"agent"``, or ``None``."""
        return self._key_type

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> httpx.Response:
        retries = max_retries if max_retries is not None else self.max_retries
        idempotency_key: str | None = None

        for attempt in range(retries + 1):
            headers: dict[str, str] = {}
            if method == "POST" and attempt > 0:
                if idempotency_key is None:
                    idempotency_key = os.urandom(16).hex()
                headers[_IDEMPOTENCY_HEADER] = idempotency_key

            try:
                response = self._client.request(
                    method,
                    path,
                    json=json,
                    params=_strip_none(params),
                    headers=headers,
                )
            except httpx.TimeoutException as exc:
                if attempt >= retries:
                    raise APITimeoutError(request=exc.request) from exc
                time.sleep(_sleep_time(attempt, None))
                continue
            except httpx.ConnectError as exc:
                if attempt >= retries:
                    raise APIConnectionError(request=exc.request) from exc
                time.sleep(_sleep_time(attempt, None))
                continue

            if response.status_code in _RETRYABLE_STATUS_CODES and attempt < retries:
                retry_after = response.headers.get("Retry-After")
                time.sleep(_sleep_time(attempt, retry_after))
                continue

            if response.status_code >= 400:
                body = _safe_json(response)
                raise _make_status_error(response, body)

            return response

        raise APIConnectionError("Max retries exceeded.")

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> SyncAPIClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


class AsyncAPIClient:
    """Asynchronous HTTP client for the Chronary API."""

    _client: httpx.AsyncClient
    _owns_client: bool
    _api_key: str | None
    _key_type: KeyType | None
    base_url: str
    max_retries: int

    def __init__(
        self,
        *,
        api_key: str | None = None,
        agent_key: str | None = None,
        base_url: str = "https://api.chronary.ai",
        timeout: float = 60.0,
        max_retries: int = 2,
        httpx_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key, self._key_type = _resolve_credentials(api_key, agent_key)
        self.base_url = base_url
        self.max_retries = max_retries

        if httpx_client is not None:
            self._client = httpx_client
            self._owns_client = False
        else:
            self._client = httpx.AsyncClient(
                base_url=base_url,
                headers=_default_headers(self._api_key),
                timeout=timeout,
            )
            self._owns_client = True

    @property
    def key_type(self) -> KeyType | None:
        """Which credential the client is using — ``"backend"``, ``"agent"``, or ``None``."""
        return self._key_type

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> httpx.Response:
        retries = max_retries if max_retries is not None else self.max_retries
        idempotency_key: str | None = None

        for attempt in range(retries + 1):
            headers: dict[str, str] = {}
            if method == "POST" and attempt > 0:
                if idempotency_key is None:
                    idempotency_key = os.urandom(16).hex()
                headers[_IDEMPOTENCY_HEADER] = idempotency_key

            try:
                response = await self._client.request(
                    method,
                    path,
                    json=json,
                    params=_strip_none(params),
                    headers=headers,
                )
            except httpx.TimeoutException as exc:
                if attempt >= retries:
                    raise APITimeoutError(request=exc.request) from exc
                await _async_sleep(_sleep_time(attempt, None))
                continue
            except httpx.ConnectError as exc:
                if attempt >= retries:
                    raise APIConnectionError(request=exc.request) from exc
                await _async_sleep(_sleep_time(attempt, None))
                continue

            if response.status_code in _RETRYABLE_STATUS_CODES and attempt < retries:
                retry_after = response.headers.get("Retry-After")
                await _async_sleep(_sleep_time(attempt, retry_after))
                continue

            if response.status_code >= 400:
                body = _safe_json(response)
                raise _make_status_error(response, body)

            return response

        raise APIConnectionError("Max retries exceeded.")

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> AsyncAPIClient:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()


async def _async_sleep(seconds: float) -> None:
    import anyio

    await anyio.sleep(seconds)


def _strip_none(params: dict[str, Any] | None) -> dict[str, Any] | None:
    if params is None:
        return None
    return {k: v for k, v in params.items() if v is not None}


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return None
