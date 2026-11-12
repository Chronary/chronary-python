from __future__ import annotations

from typing import Literal, Optional
from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

#: Who acted: a console ``session``, the Organization key (``org_key``), an
#: Agent key (``agent_key``), or Chronary itself (``system``).
AuditActorType = Literal["session", "org_key", "agent_key", "system"]

#: Response status class filter.
AuditStatusClass = Literal["2xx", "3xx", "4xx", "5xx"]

#: Action category filter.
AuditCategory = Literal[
    "account",
    "keys",
    "agents",
    "calendars",
    "events",
    "scheduling",
    "webhooks",
    "human_calendars",
    "billing",
    "security",
]


class AuditLogEntry(ChronaryModel):
    """A single audit-log entry for a mutating API operation or auth event."""

    id: str
    action: str
    actor_key_prefix: Optional[str] = None
    #: ``session``, ``org_key``, ``agent_key`` or ``system``; None on older
    #: entries that could not be attributed. Kept as ``str`` so a new actor
    #: type never breaks parsing.
    actor_type: Optional[str] = None
    #: API key id for a key, the organization id for a console session.
    actor_id: Optional[str] = None
    #: Key label (or key prefix), session email, or ``Chronary``.
    actor_label: Optional[str] = None
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


def _add_actor_filters(
    params: dict[str, str],
    *,
    actor_type: Optional[str],
    actor_id: Optional[str],
    request_id: Optional[str],
    resource: Optional[str],
    status_class: Optional[str],
    category: Optional[str],
) -> None:
    """Add the #1176 filters that are set to ``params``."""
    for key, value in (
        ("actor_type", actor_type),
        ("actor_id", actor_id),
        ("request_id", request_id),
        ("resource", resource),
        ("status_class", status_class),
        ("category", category),
    ):
        if value is not None:
            params[key] = value


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
        actor_type: Optional[AuditActorType] = None,
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
        resource: Optional[str] = None,
        status_class: Optional[AuditStatusClass] = None,
        category: Optional[AuditCategory] = None,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> AuditLogResponse:
        """List audit-log entries for the calling organization.

        Results are ordered by time descending and clamped to the per-tier
        retention window (Free: 3 days, Pro: 90 days, Custom: per contract).
        Only org-level API keys may call this endpoint.

        Args:
            from_: Lower bound (inclusive, ISO-8601). Note the trailing
                underscore — ``from`` is a Python reserved word.
            to: Upper bound (inclusive, ISO-8601). Defaults to now.
            action: Filter by exact action, e.g. ``agent.create``. Legacy
                names (``key.create``, ``key.delete``, ``key.regenerate``)
                are matched by their current names.
            actor_key_prefix: Filter by the first 20 chars of the actor key.
            actor_type: Filter by who acted: ``session``, ``org_key``,
                ``agent_key`` or ``system``.
            actor_id: Filter by actor id (an API key id, or the organization
                id for console sessions).
            request_id: Filter by the request id of the original call.
            resource: Filter by an entity id the request touched, or a bare
                id prefix such as ``cal_``.
            status_class: Filter by response status class (``2xx``..``5xx``).
            category: Filter by action category, e.g. ``keys``.
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
        _add_actor_filters(
            params,
            actor_type=actor_type,
            actor_id=actor_id,
            request_id=request_id,
            resource=resource,
            status_class=status_class,
            category=category,
        )
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
        actor_type: Optional[AuditActorType] = None,
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
        resource: Optional[str] = None,
        status_class: Optional[AuditStatusClass] = None,
        category: Optional[AuditCategory] = None,
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
        _add_actor_filters(
            params,
            actor_type=actor_type,
            actor_id=actor_id,
            request_id=request_id,
            resource=resource,
            status_class=status_class,
            category=category,
        )
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = str(limit)
        resp = await self._request("GET", _AUDIT_LOG_PATH, params=params or None, max_retries=max_retries)
        return self._build(AuditLogResponse, resp)
