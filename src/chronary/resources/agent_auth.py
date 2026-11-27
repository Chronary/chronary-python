from __future__ import annotations

from typing import Any, Literal

from typing_extensions import NotRequired, Required, TypedDict

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource

# ---------------------------------------------------------------------------
# Request param types
# ---------------------------------------------------------------------------


# Longest ``heard_about`` the API keeps (#2651); longer text is cut before sending.
_HEARD_ABOUT_MAX = 200


class AgentSignUpParams(TypedDict):
    email: Required[str]
    agent_name: Required[str]
    tos_version: Required[str]
    heard_about: NotRequired[str]


class AgentSignUpAnonymousParams(TypedDict):
    agent_name: Required[str]
    tos_version: Required[str]
    source: NotRequired[Literal["playground", "agent"]]


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


class AgentSignUpAnonymousResponse(ChronaryModel):
    """Response from ``POST /v1/agent/sign-up/anonymous`` (HTTP 201).

    A claimable organization with no email. ``api_key`` works at once at
    Sandbox limits until ``expires_at``. Give ``claim_url`` to the person who
    should own the calendar: opening it while signed in to the console moves
    everything into their account, and this key stops working. Both are shown
    once; unclaimed, the org and its data are deleted after ``expires_at``.
    """

    org_id: str
    agent_id: str
    api_key: str
    claim_url: str
    expires_at: str
    plan: str


class AgentVerifyResponse(ChronaryModel):
    """Response from ``POST /v1/agent/verify``."""

    verified: Literal[True]
    message: str
    sandbox_promotion: Literal["promoted", "capacity_full"] | None = None
    """``promoted``: the org left the Sandbox tier. ``capacity_full``: the email
    is verified, but early access is full, so the org keeps Sandbox limits until
    a spot opens. ``None``: the org was not on Sandbox."""


# ---------------------------------------------------------------------------
# Sync / Async resources
# ---------------------------------------------------------------------------

_SIGN_UP_PATH = "/v1/agent/sign-up"
_SIGN_UP_ANONYMOUS_PATH = "/v1/agent/sign-up/anonymous"
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
        heard_about: str | None = None,
        max_retries: int | None = None,
    ) -> AgentSignUpResponse:
        body: dict[str, Any] = {
            "email": email,
            "agent_name": agent_name,
            "tos_version": tos_version,
        }
        # Optional: how the agent found Chronary (plain text, at most 200
        # characters). Stored for a new organization only; never returned.
        if heard_about is not None:
            # Cut to 200 characters so a long answer never costs the sign-up.
            body["heard_about"] = heard_about[:_HEARD_ABOUT_MAX]
        resp = self._request("POST", _SIGN_UP_PATH, json=body, max_retries=max_retries)
        return self._build(AgentSignUpResponse, resp)

    def sign_up_anonymous(
        self,
        *,
        agent_name: str,
        tos_version: str,
        source: Literal["playground", "agent"] | None = None,
        max_retries: int | None = 0,
    ) -> AgentSignUpAnonymousResponse:
        """Sign up without an email: a claimable organization.

        No authentication required. The org sends and receives no email and
        cannot create webhook endpoints or call :py:meth:`verify`. Raises on
        409 ``tos_version_stale``, 429 ``rate_limit_error`` and 503
        (``anonymous_signup_disabled``, ``signups_paused``,
        ``anonymous_signup_capacity``, ``temporarily_disabled``).

        Sent once by default (``max_retries=0``): the server does not dedupe
        this POST, so a retry after a lost response (a 5xx or read timeout
        after the org was created) would create a second claimable org.
        Pass ``max_retries`` to opt back in; ``None`` also means 0.
        """
        body: dict[str, Any] = {"agent_name": agent_name, "tos_version": tos_version}
        if source is not None:
            body["source"] = source
        resp = self._request(
            "POST", _SIGN_UP_ANONYMOUS_PATH,
            json=body,
            # None means 0 here too, not the client default (#2690).
            max_retries=max_retries if max_retries is not None else 0,
        )
        return self._build(AgentSignUpAnonymousResponse, resp)

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
        heard_about: str | None = None,
        max_retries: int | None = None,
    ) -> AgentSignUpResponse:
        body: dict[str, Any] = {
            "email": email,
            "agent_name": agent_name,
            "tos_version": tos_version,
        }
        # Optional: how the agent found Chronary (plain text, at most 200
        # characters). Stored for a new organization only; never returned.
        if heard_about is not None:
            # Cut to 200 characters so a long answer never costs the sign-up.
            body["heard_about"] = heard_about[:_HEARD_ABOUT_MAX]
        resp = await self._request(
            "POST", _SIGN_UP_PATH, json=body, max_retries=max_retries
        )
        return self._build(AgentSignUpResponse, resp)

    async def sign_up_anonymous(
        self,
        *,
        agent_name: str,
        tos_version: str,
        source: Literal["playground", "agent"] | None = None,
        max_retries: int | None = 0,
    ) -> AgentSignUpAnonymousResponse:
        """Sign up without an email: a claimable organization.

        No authentication required. The org sends and receives no email and
        cannot create webhook endpoints or call :py:meth:`verify`. Raises on
        409 ``tos_version_stale``, 429 ``rate_limit_error`` and 503
        (``anonymous_signup_disabled``, ``signups_paused``,
        ``anonymous_signup_capacity``, ``temporarily_disabled``).

        Sent once by default (``max_retries=0``): the server does not dedupe
        this POST, so a retry after a lost response (a 5xx or read timeout
        after the org was created) would create a second claimable org.
        Pass ``max_retries`` to opt back in; ``None`` also means 0.
        """
        body: dict[str, Any] = {"agent_name": agent_name, "tos_version": tos_version}
        if source is not None:
            body["source"] = source
        resp = await self._request(
            "POST", _SIGN_UP_ANONYMOUS_PATH,
            json=body,
            # None means 0 here too, not the client default (#2690).
            max_retries=max_retries if max_retries is not None else 0,
        )
        return self._build(AgentSignUpAnonymousResponse, resp)

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
