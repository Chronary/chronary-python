# Chronary Python SDK

The official Python client for the [Chronary](https://chronary.ai) calendar-as-a-service API.

## Installation

```bash
pip install chronary
```

Requires Python 3.10+.

## Quickstart

### Synchronous

```python
from chronary import Chronary

client = Chronary(api_key="chr_sk_...")

# Create a calendar
calendar = client.calendars.create(name="Sales Team", timezone="America/New_York")

# Create an event
event = client.events.create(
    calendar.id,
    title="Strategy Sync",
    start_time="2026-03-28T14:00:00Z",
    end_time="2026-03-28T14:30:00Z",
)

# Check availability
free_slots = client.availability.get(
    "agt_abc123",
    start="2026-03-28T09:00:00Z",
    end="2026-03-28T17:00:00Z",
    slot_duration="30m",
)
```

### Asynchronous

```python
from chronary import AsyncChronary

async with AsyncChronary(api_key="chr_sk_...") as client:
    agent = await client.agents.create(name="Support Bot", type="ai")
    calendars = await client.agents.calendars.list(agent.id)
```

## Configuration

### Environment variable

```bash
export CHRONARY_API_KEY="chr_sk_..."
```

```python
# No api_key argument needed when the env var is set
client = Chronary()
```

### Custom options

```python
client = Chronary(
    api_key="chr_sk_...",
    base_url="https://api.chronary.ai",  # default
    timeout=60.0,                         # seconds, default 60
    max_retries=2,                        # default 2
)
```

### Custom httpx client

```python
import httpx

transport = httpx.HTTPTransport(retries=3)
http_client = httpx.Client(transport=transport)

client = Chronary(api_key="chr_sk_...", httpx_client=http_client)
```

The SDK adds its `Authorization`, `User-Agent` and `Accept` headers to every request sent through your client unless your client already sets them, and uses its own `base_url` when your client has none. Your client's timeout applies unless you also pass `timeout=` to `Chronary`.

## Resources

| Resource | Accessor | Methods |
|---|---|---|
| Agents | `client.agents` | `create`, `list`, `get`, `update`, `delete` |
| Calendars | `client.calendars` | `create`, `list`, `get`, `update`, `delete` |
| Events | `client.events` | `create`, `list`, `get`, `update`, `delete` |
| Webhooks | `client.webhooks` | `create`, `list`, `get`, `update`, `delete` |
| iCal Subscriptions | `client.ical_subscriptions` | `create`, `list`, `get`, `update`, `delete`, `sync` |
| Availability | `client.availability` | `get`, `get_calendar`, `find_meeting_time` |
| Usage | `client.usage` | `get` |

### Agent-scoped resources

```python
# Calendars owned by an agent
client.agents.calendars.create("agt_abc123", name="My Cal", timezone="UTC")
client.agents.calendars.list("agt_abc123")

# Events across all of an agent's calendars
client.agents.events.list("agt_abc123", start_after="2026-03-01T00:00:00Z")

# Agent availability
client.agents.availability.get("agt_abc123", start="...", end="...")
```

## Pagination

List methods return a pager with `auto_paging_iter()` for transparent pagination:

```python
pager = client.agents.list()

# Iterate through all pages automatically
for agent in pager.auto_paging_iter():
    print(agent.name)

# Or access the current page directly
print(pager.data)       # list of items
print(pager.total)      # total count
print(pager.has_more)   # whether more pages exist
```

`agents.list()`, `calendars.list()`, `agents.calendars.list()` and `events.list_all()` page by cursor: `auto_paging_iter()` follows `next_cursor`, so it is not limited by the API's 10,000-row cap on `offset`. For manual paging, pass `pager.next_cursor` as `cursor=` to the same method. Other lists page by offset.

## Error handling

```python
from chronary import Chronary, NotFoundError, RateLimitError, APIError

client = Chronary()

try:
    agent = client.agents.get("agt_nonexistent")
except NotFoundError:
    print("Agent not found")
except RateLimitError:
    print("Slow down")
except APIError as e:
    print(f"{e.status_code}: {e.message}")
```

All errors carry `.status_code`, `.message`, `.request_id`, `.error_type`, and `.body`.

## Per-request options

Override retries on a per-call basis:

```python
agent = client.agents.get("agt_abc123", max_retries=5)
```

## Webhook verification

Verify incoming webhook signatures using HMAC-SHA256:

```python
from chronary.webhook import verify_signature, SignatureVerificationError

try:
    verify_signature(
        payload=request.body,
        headers=request.headers,
        secret=webhook_secret,
    )
    # signature valid — process the event
except SignatureVerificationError:
    # reject the request (e.g. return 401)
    ...
```

Verification checks `X-Signature-V2`, which covers the body, `X-Timestamp`, `X-Delivery-Id`, `X-Chronary-Event-Type`, `X-Chronary-Test` and `X-Chronary-Replay-Of`; the deprecated v1 `X-Signature` is not accepted. `unwrap()` verifies and returns `type`, `data`, `delivery_id`, `test` and `replay_of`, all covered by the signature, so deduplicate on `event["delivery_id"]`.

## Request IDs

Every response model carries an `_request_id` attribute for correlating with server logs:

```python
agent = client.agents.get("agt_abc123")
print(agent._request_id)  # "req_..."
```

## Plans & limits

Chronary enforces a per-key rate limit and per-org monthly quotas that vary by plan:

| | Free | Developer | Pro |
|---|---|---|---|
| Rate limit | 10 req/s | 25 req/s | 50 req/s |
| Webhook delivery retries | 4 | 6 | 8 |
| Agents | 1 | 10 | 50 |
| Calendars | 1 | 50 | 250 |
| Events / mo | 100 | 15,000 | 125,000 |
| API calls / mo | 1,000 | 200,000 | 1,000,000 |
| Webhook deliveries / mo | 1,000 | 25,000 | 250,000 |
| Scheduling proposals / mo | — | 1,000 | unlimited |
| Per-agent API keys (`chr_ak_*`) | — | 10 | 50 |
| Paid-plan features | — | all | all |

Paid-plan features are scheduling proposals, temporal holds, cross-agent availability, per-agent API keys, and webhook delivery replay and secret rotation. Developer and Pro have the same features and differ only in their limits.

Paid-plan feature calls raise `APIError` (status 403) on Free. The SDK automatically retries `429` and `5xx` responses with exponential backoff (`max_retries`), except a monthly quota error (`quota_exceeded`) and any refusal whose `Retry-After` is longer than 60 seconds (an iCal sync cooldown, a daily sign-up cap), which raise at once. See <https://docs.chronary.ai/resources/rate-limits/> for the full matrix.

## Security and support

Report vulnerabilities to [security@chronary.ai](mailto:security@chronary.ai) or through private vulnerability reporting on this package's GitHub repository. Please don't open a public issue. Read the full [security policy](https://github.com/Chronary/.github/blob/main/SECURITY.md).

Version 0.x is supported with security fixes until at least **April 2031**. Fixes ship in a new 0.x release, so keep up with the latest one. Supported versions and end dates for every Chronary package are listed in the [security policy](https://github.com/Chronary/.github/blob/main/SECURITY.md#supported-versions).

## License

Apache-2.0
