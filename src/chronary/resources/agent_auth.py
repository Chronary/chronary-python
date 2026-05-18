from __future__ import annotations

from typing import Any, Literal

from typing_extensions import Required, TypedDict

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource

# ---------------------------------------------------------------------------
# Request param types
# ---------------------------------------------------------------------------


class AgentSignUpParams(TypedDict):
    email: Required[str]
    agent_name: Required[str]
    tos_version: Required[str]


class AgentVerifyParams(TypedDict):
    otp: Required[str]


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class AgentSignUpResponse(ChronaryModel):
    """Response from ``POST /v1/agent/sign-up``.

    The endpoint always returns the same opaque ``message`` to prevent email
    enumeration. Only the **new-org** branch additionally includes credentials
    (``org_id``, ``agent_id``, ``api_key``); the existing-org dedup branch
    returns just the message.

    Use :pyattr:`is_new_org` to check which branch fired before reading the
    credential fields.
    """

    message: str
    org_id: str | None = None
    agent_id: str | None = None
    api_key: str | None = None
    """API key. Restricted to the verify endpoint until OTP succeeds."""

    @property
    def is_new_org(self) -> bool:
        """True iff the response carries credentials for a freshly-created org."""
        return self.api_key is not None


class AgentVerifyResponse(ChronaryModel):
    """Response from ``POST /v1/agent/verify``."""

    verified: Literal[True]
    message: str


# ---------------------------------------------------------------------------
# Sync / Async resources
# ---------------------------------------------------------------------------

_SIGN_UP_PATH = "/v1/agent/sign-up"
_VERIFY_PATH = "/v1/agent/verify"


class AgentAuth(SyncAPIResource):
    """``client.agent_auth`` — agent signup + email verification.

    The signup flow is two requests:

    1. :py:meth:`sign_up` — call from an unauthenticated client. The response
       carries a restricted ``api_key`` (only valid for ``/v1/agent/verify``).
    2. :py:meth:`verify` — call from a second client constructed with the
       restricted ``api_key``. On success the key unlocks the full API.

    The existing-org dedup branch returns no credentials. Always check
    :pyattr:`AgentSignUpResponse.is_new_org` before accessing keys.
    """

    def sign_up(
        self,
        *,
        email: str,
        agent_name: str,
        tos_version: str,
        max_retries: int | None = None,
    ) -> AgentSignUpResponse:
        body: dict[str, Any] = {
            "email": email,
            "agent_name": agent_name,
            "tos_version": tos_version,
        }
        resp = self._request("POST", _SIGN_UP_PATH, json=body, max_retries=max_retries)
        return self._build(AgentSignUpResponse, resp)

    def verify(
        self,
        *,
        otp: str,
        max_retries: int | None = None,
    ) -> AgentVerifyResponse:
        resp = self._request(
            "POST", _VERIFY_PATH, json={"otp": otp}, max_retries=max_retries
        )
        return self._build(AgentVerifyResponse, resp)


class AsyncAgentAuth(AsyncAPIResource):
    """Async counterpart to :class:`AgentAuth`."""

    async def sign_up(
        self,
        *,
        email: str,
        agent_name: str,
        tos_version: str,
        max_retries: int | None = None,
    ) -> AgentSignUpResponse:
        body: dict[str, Any] = {
            "email": email,
            "agent_name": agent_name,
            "tos_version": tos_version,
        }
        resp = await self._request(
            "POST", _SIGN_UP_PATH, json=body, max_retries=max_retries
        )
        return self._build(AgentSignUpResponse, resp)

    async def verify(
        self,
        *,
        otp: str,
        max_retries: int | None = None,
    ) -> AgentVerifyResponse:
        resp = await self._request(
            "POST", _VERIFY_PATH, json={"otp": otp}, max_retries=max_retries
        )
        return self._build(AgentVerifyResponse, resp)
