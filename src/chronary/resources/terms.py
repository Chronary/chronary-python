from __future__ import annotations

from datetime import datetime  # noqa: TCH003 -- Pydantic needs this at runtime
from typing import Any

from typing_extensions import Required, TypedDict

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource


class AcceptedTerms(ChronaryModel):
    """The org's terms-of-service acceptance after a re-acceptance call."""

    accepted_terms_version: str
    accepted_terms_at: datetime


class AcceptTermsParams(TypedDict):
    tos_version: Required[str]


_TERMS_ACCEPT_PATH = "/v1/terms/accept"


_ACCEPT_DOC = """Re-accept the current Chronary terms of service for the calling org.

Use this when a response carries the ``Chronary-Terms-Upgrade-Required``
header after a material ToS bump — it clears the upgrade requirement for
Bearer-key (SDK / MCP) clients that have no console session. Read the
current version from ``GET /v1/auth/terms/current`` and pass it verbatim.

**Authentication:** org-level API keys (``chr_sk_*``) only — agent-scoped
keys cannot accept org-wide terms (403). A stale version returns 409
``tos_version_stale`` with the current version in the error body.
"""


class Terms(SyncAPIResource):
    """client.terms -- terms-of-service re-acceptance operations."""

    def accept(
        self,
        *,
        tos_version: str,
        max_retries: int | None = None,
    ) -> AcceptedTerms:
        body: dict[str, Any] = {"tos_version": tos_version}
        resp = self._request(
            "POST", _TERMS_ACCEPT_PATH, json=body, max_retries=max_retries
        )
        return self._build(AcceptedTerms, resp)

    accept.__doc__ = _ACCEPT_DOC


class AsyncTerms(AsyncAPIResource):
    """client.terms -- async terms-of-service re-acceptance operations."""

    async def accept(
        self,
        *,
        tos_version: str,
        max_retries: int | None = None,
    ) -> AcceptedTerms:
        body: dict[str, Any] = {"tos_version": tos_version}
        resp = await self._request(
            "POST", _TERMS_ACCEPT_PATH, json=body, max_retries=max_retries
        )
        return self._build(AcceptedTerms, resp)

    accept.__doc__ = _ACCEPT_DOC
