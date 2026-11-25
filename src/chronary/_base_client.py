from __future__ import annotations

import os
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
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
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_BACKOFF_BASE = 0.5
_BACKOFF_MAX = 8.0
_JITTER_FACTOR = 0.25
# Upper bound on a server-supplied Retry-After, matching the TypeScript SDK's
# MAX_RETRY_DELAY (60s). A monthly quota 429 sends Retry-After = seconds to
# the end of the month and the daily feedback cap sends seconds to UTC
# midnight; honouring those verbatim would block the caller for hours or weeks.
# A refusal whose Retry-After is above this is not retried at all (#2558).
_RETRY_AFTER_MAX = 60.0
_IDEMPOTENCY_HEADER = "Idempotency-Key"
_DEFAULT_TIMEOUT = 60.0
# httpx's own defaults: a caller's client still carrying these has not set them.
_HTTPX_DEFAULT_ACCEPT = "*/*"
_HTTPX_DEFAULT_UA_PREFIX = "python-httpx/"


def _default_headers(api_key: str | None) -> dict[str, str]:
    # api_key is optional — some endpoints (plans.list, agent_auth.sign_up) do
    # not require auth. When a caller invokes an authed endpoint without a key,
    # the server returns 401 and the SDK surfaces it as AuthenticationError —
    # same error shape as if the key were explicitly wrong.
    headers = {
        "User-Agent": f"chronary-py/{__version__}",
        "Accept": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _is_quota_exceeded(response: httpx.Response) -> bool:
    """True for a 429 whose body says ``quota_exceeded`` (a monthly plan limit).

    Retrying cannot succeed until the limit resets or the plan changes, so the
    request loops raise ``QuotaExceededError`` at once instead (#1936).
    """
    if response.status_code != 429:
        return False
    body = _safe_json(response)
    error_obj = body.get("error") if isinstance(body, dict) else None
    return isinstance(error_obj, dict) and error_obj.get("type") == "quota_exceeded"


def _retry_after_seconds(retry_after: str | None) -> float | None:
    """A server Retry-After in seconds: delta-seconds or an HTTP date.

    ``None`` when missing, unparseable or NaN. A date in the past is 0.
    """
    if retry_after is None:
        return None
    try:
        seconds = float(retry_after)
    except ValueError:
        try:
            at = parsedate_to_datetime(retry_after)
        except (TypeError, ValueError, IndexError):
            return None
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        return max((at - datetime.now(timezone.utc)).total_seconds(), 0.0)
    return None if seconds != seconds else seconds  # NaN


def _retry_after_beyond_cap(retry_after: str | None) -> bool:
    """True when a server Retry-After is longer than the 60 s retry cap.

    Such a refusal (an iCal manual-sync cooldown, a daily sign-up cap, a
    network sign-up budget) cannot succeed inside the retry window, so the
    request loops raise it at once instead of sleeping 60 s per attempt and
    then raising the same error (#2558).
    """
    seconds = _retry_after_seconds(retry_after)
    return seconds is not None and seconds > _RETRY_AFTER_MAX


def _sleep_time(attempt: int, retry_after: str | None) -> float:
    """Calculate sleep duration: the server's Retry-After (capped), else
    exponential backoff with jitter."""
    seconds = _retry_after_seconds(retry_after)
    if seconds is not None:
        return min(max(seconds, 0.0), _RETRY_AFTER_MAX)
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


def _custom_client_overrides(
    httpx_client: httpx.Client | httpx.AsyncClient, base_url: str, api_key: str | None
) -> tuple[str, dict[str, str]]:
    """What a caller-supplied httpx client needs added to each request (#2520).

    The SDK sets ``base_url`` and its headers only on a client it builds
    itself. A caller's client gets the SDK's ``base_url`` prefixed to each path
    when it has no base_url of its own (the README example), and each SDK
    header the client does not already set: ``Authorization`` only when the
    client has none, ``User-Agent`` and ``Accept`` only while the client still
    carries httpx's defaults for them.
    """
    request_base = "" if str(httpx_client.base_url) else base_url.rstrip("/")
    own = httpx_client.headers  # case-insensitive
    headers: dict[str, str] = {}
    for name, value in _default_headers(api_key).items():
        current = own.get(name)
        if name == "Authorization":
            caller_set = current is not None
        elif name == "User-Agent":
            caller_set = current is not None and not current.startswith(_HTTPX_DEFAULT_UA_PREFIX)
        else:  # Accept
            caller_set = current is not None and current != _HTTPX_DEFAULT_ACCEPT
        if not caller_set:
            headers[name] = value
    return request_base, headers


class SyncAPIClient:
    """Synchronous HTTP client for the Chronary API."""

    _client: httpx.Client
    _owns_client: bool
    _api_key: str | None
    _key_type: KeyType | None
    base_url: str
    max_retries: int
    # Applied per request when the caller supplied the httpx client (#2520):
    # the SDK's base_url (only when that client has none), the SDK headers the
    # client does not set, and ``timeout`` only when it was passed explicitly.
    _request_base: str
    _request_headers: dict[str, str]
    _request_timeout: float | None

    def __init__(
        self,
        *,
        api_key: str | None = None,
        agent_key: str | None = None,
        base_url: str = "https://api.chronary.ai",
        timeout: float | None = None,
        max_retries: int = 2,
        httpx_client: httpx.Client | None = None,
    ) -> None:
        self._api_key, self._key_type = _resolve_credentials(api_key, agent_key)
        self.base_url = base_url
        self.max_retries = max_retries

        if httpx_client is not None:
            self._client = httpx_client
            self._owns_client = False
            self._request_base, self._request_headers = _custom_client_overrides(
                httpx_client, base_url, self._api_key
            )
            self._request_timeout = timeout
        else:
            self._client = httpx.Client(
                base_url=base_url,
                headers=_default_headers(self._api_key),
                timeout=timeout if timeout is not None else _DEFAULT_TIMEOUT,
            )
            self._owns_client = True
            self._request_base, self._request_headers = "", {}
            self._request_timeout = None

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
        idempotency_key: str | None = None,
    ) -> httpx.Response:
        retries = max_retries if max_retries is not None else self.max_retries
        request_headers: dict[str, str] = dict(self._request_headers)
        if method.upper() in _MUTATING_METHODS:
            request_headers[_IDEMPOTENCY_HEADER] = idempotency_key or os.urandom(16).hex()

        for attempt in range(retries + 1):
            try:
                response = self._client.request(
                    method,
                    self._request_base + path,
                    json=json,
                    params=_strip_none(params),
                    headers=request_headers,
                    **_timeout_kwargs(self._request_timeout),
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

            if (
                response.status_code in _RETRYABLE_STATUS_CODES
                and attempt < retries
                and not _is_quota_exceeded(response)
                and not _retry_after_beyond_cap(response.headers.get("Retry-After"))
            ):
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
    # Applied per request when the caller supplied the httpx client (#2520):
    # the SDK's base_url (only when that client has none), the SDK headers the
    # client does not set, and ``timeout`` only when it was passed explicitly.
    _request_base: str
    _request_headers: dict[str, str]
    _request_timeout: float | None

    def __init__(
        self,
        *,
        api_key: str | None = None,
        agent_key: str | None = None,
        base_url: str = "https://api.chronary.ai",
        timeout: float | None = None,
        max_retries: int = 2,
        httpx_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key, self._key_type = _resolve_credentials(api_key, agent_key)
        self.base_url = base_url
        self.max_retries = max_retries

        if httpx_client is not None:
            self._client = httpx_client
            self._owns_client = False
            self._request_base, self._request_headers = _custom_client_overrides(
                httpx_client, base_url, self._api_key
            )
            self._request_timeout = timeout
        else:
            self._client = httpx.AsyncClient(
                base_url=base_url,
                headers=_default_headers(self._api_key),
                timeout=timeout if timeout is not None else _DEFAULT_TIMEOUT,
            )
            self._owns_client = True
            self._request_base, self._request_headers = "", {}
            self._request_timeout = None

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
        idempotency_key: str | None = None,
    ) -> httpx.Response:
        retries = max_retries if max_retries is not None else self.max_retries
        request_headers: dict[str, str] = dict(self._request_headers)
        if method.upper() in _MUTATING_METHODS:
            request_headers[_IDEMPOTENCY_HEADER] = idempotency_key or os.urandom(16).hex()

        for attempt in range(retries + 1):
            try:
                response = await self._client.request(
                    method,
                    self._request_base + path,
                    json=json,
                    params=_strip_none(params),
                    headers=request_headers,
                    **_timeout_kwargs(self._request_timeout),
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

            if (
                response.status_code in _RETRYABLE_STATUS_CODES
                and attempt < retries
                and not _is_quota_exceeded(response)
                and not _retry_after_beyond_cap(response.headers.get("Retry-After"))
            ):
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


def _timeout_kwargs(timeout: float | None) -> dict[str, Any]:
    # Omitting ``timeout`` keeps the httpx client's own setting.
    return {} if timeout is None else {"timeout": timeout}


def _strip_none(params: dict[str, Any] | None) -> dict[str, Any] | None:
    if params is None:
        return None
    return {k: v for k, v in params.items() if v is not None}


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return None
