from __future__ import annotations

from typing import Any, Literal

from typing_extensions import Required, TypedDict

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource

# ---------------------------------------------------------------------------
# Request param types
# ---------------------------------------------------------------------------


class WaitlistJoinParams(TypedDict, total=False):
    email: Required[str]
    name: str
    tos_version: str
    intent: str


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class WaitlistedOrg(ChronaryModel):
    """Deprecated: the waitlist join no longer returns the entry. Kept so
    existing imports keep working."""

    id: str
    name: str
    email: str
    is_waitlisted: Literal[True]
    waitlisted_at: str
    signup_source: str


class WaitlistJoinResponse(ChronaryModel):
    """Response from ``POST /v1/waitlist`` (HTTP 202).

    The same body whether the email is new, already on the list, or has an
    active account, so it can't be used to look up other people's accounts.
    Only a new email is sent the confirmation email.
    """

    waitlisted: Literal[True]
    message: str


_JOIN_PATH = "/v1/waitlist"


class Waitlist(SyncAPIResource):
    """``client.waitlist`` — soft-launch waitlist enrollment.

    Used while open sign-up is gated. Adds the email to the waitlist; an
    account is created only when a founder approves it and the person accepts
    the emailed invite.

    No authentication required — invoke on a ``Chronary`` client constructed
    with no ``api_key``.
    """

    def join(
        self,
        *,
        email: str,
        name: str | None = None,
        tos_version: str | None = None,
        intent: str | None = None,
        max_retries: int | None = None,
    ) -> WaitlistJoinResponse:
        body: dict[str, Any] = {"email": email}
        if name is not None:
            body["name"] = name
        if tos_version is not None:
            body["tos_version"] = tos_version
        if intent is not None:
            body["intent"] = intent
        resp = self._request("POST", _JOIN_PATH, json=body, max_retries=max_retries)
        return self._build(WaitlistJoinResponse, resp)


class AsyncWaitlist(AsyncAPIResource):
    """Async counterpart to :class:`Waitlist`."""

    async def join(
        self,
        *,
        email: str,
        name: str | None = None,
        tos_version: str | None = None,
        intent: str | None = None,
        max_retries: int | None = None,
    ) -> WaitlistJoinResponse:
        body: dict[str, Any] = {"email": email}
        if name is not None:
            body["name"] = name
        if tos_version is not None:
            body["tos_version"] = tos_version
        if intent is not None:
            body["intent"] = intent
        resp = await self._request(
            "POST", _JOIN_PATH, json=body, max_retries=max_retries
        )
        return self._build(WaitlistJoinResponse, resp)
