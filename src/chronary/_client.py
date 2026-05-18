from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._base_client import AsyncAPIClient, SyncAPIClient
from .resources import (
    Account,
    AgentAuth,
    Agents,
    AsyncAccount,
    AsyncAgentAuth,
    AsyncAgents,
    AsyncAvailability,
    AsyncCalendars,
    AsyncEvents,
    AsyncFeedback,
    AsyncICalSubscriptions,
    AsyncKeys,
    AsyncPlans,
    AsyncScheduling,
    AsyncAuditLog,
    AsyncUsage,
    AsyncWaitlist,
    AsyncWebhooks,
    AuditLog,
    Availability,
    Calendars,
    Events,
    Feedback,
    ICalSubscriptions,
    Keys,
    Plans,
    Scheduling,
    Usage,
    Waitlist,
    Webhooks,
)

if TYPE_CHECKING:
    import httpx


class Chronary(SyncAPIClient):
    """Synchronous client for the Chronary API."""

    _agents: Agents | None
    _calendars: Calendars | None
    _events: Events | None
    _webhooks: Webhooks | None
    _ical_subscriptions: ICalSubscriptions | None
    _availability: Availability | None
    _scheduling: Scheduling | None
    _usage: Usage | None
    _audit_log: AuditLog | None
    _keys: Keys | None
    _feedback: Feedback | None
    _plans: Plans | None
    _agent_auth: AgentAuth | None
    _waitlist: Waitlist | None
    _account: Account | None

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
        super().__init__(
            api_key=api_key,
            agent_key=agent_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            httpx_client=httpx_client,
        )
        self._agents = None
        self._calendars = None
        self._events = None
        self._webhooks = None
        self._ical_subscriptions = None
        self._availability = None
        self._scheduling = None
        self._usage = None
        self._audit_log = None
        self._keys = None
        self._feedback = None
        self._plans = None
        self._agent_auth = None
        self._waitlist = None
        self._account = None

    @property
    def agents(self) -> Agents:
        if self._agents is None:
            self._agents = Agents(self)
        return self._agents

    @property
    def calendars(self) -> Calendars:
        if self._calendars is None:
            self._calendars = Calendars(self)
        return self._calendars

    @property
    def events(self) -> Events:
        if self._events is None:
            self._events = Events(self)
        return self._events

    @property
    def webhooks(self) -> Webhooks:
        if self._webhooks is None:
            self._webhooks = Webhooks(self)
        return self._webhooks

    @property
    def ical_subscriptions(self) -> ICalSubscriptions:
        if self._ical_subscriptions is None:
            self._ical_subscriptions = ICalSubscriptions(self)
        return self._ical_subscriptions

    @property
    def availability(self) -> Availability:
        if self._availability is None:
            self._availability = Availability(self)
        return self._availability

    @property
    def scheduling(self) -> Scheduling:
        if self._scheduling is None:
            self._scheduling = Scheduling(self)
        return self._scheduling

    @property
    def usage(self) -> Usage:
        if self._usage is None:
            self._usage = Usage(self)
        return self._usage

    @property
    def audit_log(self) -> AuditLog:
        if self._audit_log is None:
            self._audit_log = AuditLog(self)
        return self._audit_log

    @property
    def keys(self) -> Keys:
        if self._keys is None:
            self._keys = Keys(self)
        return self._keys

    @property
    def feedback(self) -> Feedback:
        if self._feedback is None:
            self._feedback = Feedback(self)
        return self._feedback

    @property
    def plans(self) -> Plans:
        if self._plans is None:
            self._plans = Plans(self)
        return self._plans

    @property
    def agent_auth(self) -> AgentAuth:
        if self._agent_auth is None:
            self._agent_auth = AgentAuth(self)
        return self._agent_auth

    @property
    def waitlist(self) -> Waitlist:
        if self._waitlist is None:
            self._waitlist = Waitlist(self)
        return self._waitlist

    @property
    def account(self) -> Account:
        if self._account is None:
            self._account = Account(self)
        return self._account

    def __enter__(self) -> Chronary:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


class AsyncChronary(AsyncAPIClient):
    """Asynchronous client for the Chronary API."""

    _agents: AsyncAgents | None
    _calendars: AsyncCalendars | None
    _events: AsyncEvents | None
    _webhooks: AsyncWebhooks | None
    _ical_subscriptions: AsyncICalSubscriptions | None
    _availability: AsyncAvailability | None
    _scheduling: AsyncScheduling | None
    _usage: AsyncUsage | None
    _audit_log: AsyncAuditLog | None
    _keys: AsyncKeys | None
    _feedback: AsyncFeedback | None
    _plans: AsyncPlans | None
    _agent_auth: AsyncAgentAuth | None
    _waitlist: AsyncWaitlist | None
    _account: AsyncAccount | None

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
        super().__init__(
            api_key=api_key,
            agent_key=agent_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            httpx_client=httpx_client,
        )
        self._agents = None
        self._calendars = None
        self._events = None
        self._webhooks = None
        self._ical_subscriptions = None
        self._availability = None
        self._scheduling = None
        self._usage = None
        self._audit_log = None
        self._keys = None
        self._feedback = None
        self._plans = None
        self._agent_auth = None
        self._waitlist = None
        self._account = None

    @property
    def agents(self) -> AsyncAgents:
        if self._agents is None:
            self._agents = AsyncAgents(self)
        return self._agents

    @property
    def calendars(self) -> AsyncCalendars:
        if self._calendars is None:
            self._calendars = AsyncCalendars(self)
        return self._calendars

    @property
    def events(self) -> AsyncEvents:
        if self._events is None:
            self._events = AsyncEvents(self)
        return self._events

    @property
    def webhooks(self) -> AsyncWebhooks:
        if self._webhooks is None:
            self._webhooks = AsyncWebhooks(self)
        return self._webhooks

    @property
    def ical_subscriptions(self) -> AsyncICalSubscriptions:
        if self._ical_subscriptions is None:
            self._ical_subscriptions = AsyncICalSubscriptions(self)
        return self._ical_subscriptions

    @property
    def availability(self) -> AsyncAvailability:
        if self._availability is None:
            self._availability = AsyncAvailability(self)
        return self._availability

    @property
    def scheduling(self) -> AsyncScheduling:
        if self._scheduling is None:
            self._scheduling = AsyncScheduling(self)
        return self._scheduling

    @property
    def usage(self) -> AsyncUsage:
        if self._usage is None:
            self._usage = AsyncUsage(self)
        return self._usage

    @property
    def audit_log(self) -> AsyncAuditLog:
        if self._audit_log is None:
            self._audit_log = AsyncAuditLog(self)
        return self._audit_log

    @property
    def keys(self) -> AsyncKeys:
        if self._keys is None:
            self._keys = AsyncKeys(self)
        return self._keys

    @property
    def feedback(self) -> AsyncFeedback:
        if self._feedback is None:
            self._feedback = AsyncFeedback(self)
        return self._feedback

    @property
    def plans(self) -> AsyncPlans:
        if self._plans is None:
            self._plans = AsyncPlans(self)
        return self._plans

    @property
    def agent_auth(self) -> AsyncAgentAuth:
        if self._agent_auth is None:
            self._agent_auth = AsyncAgentAuth(self)
        return self._agent_auth

    @property
    def waitlist(self) -> AsyncWaitlist:
        if self._waitlist is None:
            self._waitlist = AsyncWaitlist(self)
        return self._waitlist

    @property
    def account(self) -> AsyncAccount:
        if self._account is None:
            self._account = AsyncAccount(self)
        return self._account

    async def __aenter__(self) -> AsyncChronary:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()
