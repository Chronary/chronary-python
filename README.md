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
from chronary.webhook import verify_signature

is_valid = verify_signature(
    payload=request.body,
    signature=request.headers["X-Chronary-Signature"],
    secret=webhook_secret,
)
```

## Request IDs

Every response model carries an `_request_id` attribute for correlating with server logs:

```python
agent = client.agents.get("agt_abc123")
print(agent._request_id)  # "req_..."
```

## License

Apache-2.0
