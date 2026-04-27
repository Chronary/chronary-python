from __future__ import annotations

from typing import Any

from .._resource import AsyncAPIResource, SyncAPIResource

_EXPORT_PATH = "/v1/auth/export"

_EXPORT_DOC = """Export every row this org owns as a JSON payload (GDPR Art. 15 + 20).

Includes agents, calendars, events (with decrypted titles + descriptions),
iCal subscriptions (with decrypted URL), webhook subscriptions (with
decrypted secret), availability rules, scheduling proposals, API key
prefixes, ToS acceptance history, and usage/quota counters.

**Authentication:** This endpoint is JWT-only — it returns decrypted
webhook secrets and iCal URLs that aren't normally accessible via API-key
endpoints. Configure the SDK with a console JWT (cookie value or Bearer
token from the console session) as the api_key argument. API keys
(chr_sk_* / chr_ak_*) will return 401.

In most cases, end users should download via the console UI at
console.chronary.ai/settings. The SDK method exists for programmatic use
cases (server-side compliance tooling holding a delegated JWT).

**Rate limit:** 10 exports/hour/org.
"""


class Account(SyncAPIResource):
    """client.account -- GDPR portability + erasure operations."""

    def export(self, *, max_retries: int | None = None) -> dict[str, Any]:
        resp = self._request("GET", _EXPORT_PATH, max_retries=max_retries)
        return resp  # The full DataExport JSON payload — schema in TS SDK / OpenAPI.

    export.__doc__ = _EXPORT_DOC


class AsyncAccount(AsyncAPIResource):
    """client.account -- async GDPR portability + erasure operations."""

    async def export(self, *, max_retries: int | None = None) -> dict[str, Any]:
        resp = await self._request("GET", _EXPORT_PATH, max_retries=max_retries)
        return resp

    export.__doc__ = _EXPORT_DOC
