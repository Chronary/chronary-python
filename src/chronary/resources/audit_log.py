from __future__ import annotations

from typing import Optional
from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class AuditLogEntry(ChronaryModel):
    """A single audit-log entry for a mutating API operation or auth event."""

    id: str
    action: str
    actor_key_prefix: Optional[str] = None
    agent_id: Optional[str] = None
    resource: Optional[str] = None
    ip: Optional[str] = None
    status: int
    method: str
    path: str
    duration_ms: int
    request_id: Optional[str] = None
    created_at: str


class AuditLogPagination(ChronaryModel):
    """Pagination envelope for audit-log responses."""

    next_cursor: Optional[str] = None


class AuditLogResponse(ChronaryModel):
    """Response from GET /v1/audit-log."""

    data: list[AuditLogEntry]
    pagination: AuditLogPagination
    retention_days: Optional[int] = None
    range_clamped: bool


# ---------------------------------------------------------------------------
# Sync resource
# ---------------------------------------------------------------------------

_AUDIT_LOG_PATH = "/v1/audit-log"


class AuditLog(SyncAPIResource):
    """client.audit_log — synchronous audit-log queries."""

    def list(
        self,
        *,
        from_: Optional[str] = None,
        to: Optional[str] = None,
        action: Optional[str] = None,
        actor_key_prefix: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> AuditLogResponse:
        """List audit-log entries for the calling organization.

        Results are ordered by time descending and clamped to the per-tier
        retention window (Free: 7d, Pro: 90d). Only org-level API keys may
        call this endpoint.

        Args:
            from_: Lower bound (inclusive, ISO-8601). Note the trailing
                underscore — ``from`` is a Python reserved word.
            to: Upper bound (inclusive, ISO-8601). Defaults to now.
            action: Filter by exact action, e.g. ``agent.create``.
            actor_key_prefix: Filter by the first 20 chars of the actor key.
            cursor: Opaque pagination cursor from a previous response.
            limit: Page size (1–200). Defaults to 50.
        """
        params: dict[str, str] = {}
        if from_ is not None:
            params["from"] = from_
        if to is not None:
            params["to"] = to
        if action is not None:
            params["action"] = action
        if actor_key_prefix is not None:
            params["actor_key_prefix"] = actor_key_prefix
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = str(limit)
        resp = self._request("GET", _AUDIT_LOG_PATH, params=params or None, max_retries=max_retries)
        return self._build(AuditLogResponse, resp)


# ---------------------------------------------------------------------------
# Async resource
# ---------------------------------------------------------------------------


class AsyncAuditLog(AsyncAPIResource):
    """client.audit_log — asynchronous audit-log queries."""

    async def list(
        self,
        *,
        from_: Optional[str] = None,
        to: Optional[str] = None,
        action: Optional[str] = None,
        actor_key_prefix: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> AuditLogResponse:
        """List audit-log entries. See :meth:`AuditLog.list` for parameter docs."""
        params: dict[str, str] = {}
        if from_ is not None:
            params["from"] = from_
        if to is not None:
            params["to"] = to
        if action is not None:
            params["action"] = action
        if actor_key_prefix is not None:
            params["actor_key_prefix"] = actor_key_prefix
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = str(limit)
        resp = await self._request("GET", _AUDIT_LOG_PATH, params=params or None, max_retries=max_retries)
        return self._build(AuditLogResponse, resp)
