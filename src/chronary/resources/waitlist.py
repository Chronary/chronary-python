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


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class WaitlistedOrg(ChronaryModel):
    id: str
    name: str
    email: str
    is_waitlisted: Literal[True]
    waitlisted_at: str
    signup_source: str


class WaitlistJoinResponse(ChronaryModel):
    """Response from ``POST /v1/waitlist`` (#442).

    Idempotent — calling :py:meth:`Waitlist.join` twice with the same email
    returns the existing waitlisted org row instead of erroring. An active
    (non-waitlisted) account at the same email returns 409 ``email_taken``.
    """

    data: WaitlistedOrg
    message: str


_JOIN_PATH = "/v1/waitlist"


class Waitlist(SyncAPIResource):
    """``client.waitlist`` — soft-launch waitlist enrollment.

    Used during private preview when the open signup flow is gated. Creates a
    real organization row flagged as ``is_waitlisted=True``; an admin flips
    the flag on activation, after which the holder can sign in normally.

    No authentication required — invoke on a ``Chronary`` client constructed
    with no ``api_key``.
    """

    def join(
        self,
        *,
        email: str,
        name: str | None = None,
        tos_version: str | None = None,
        max_retries: int | None = None,
    ) -> WaitlistJoinResponse:
        body: dict[str, Any] = {"email": email}
        if name is not None:
            body["name"] = name
        if tos_version is not None:
            body["tos_version"] = tos_version
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
        max_retries: int | None = None,
    ) -> WaitlistJoinResponse:
        body: dict[str, Any] = {"email": email}
        if name is not None:
            body["name"] = name
        if tos_version is not None:
            body["tos_version"] = tos_version
        resp = await self._request(
            "POST", _JOIN_PATH, json=body, max_retries=max_retries
        )
        return self._build(WaitlistJoinResponse, resp)
