# Changelog

All notable changes to `chronary` (Python SDK) will be documented in this file starting with the soft-launch release.

## 0.14.0 — unreleased

- **Breaking: webhook verification requires the v2 signature (#2569).** Chronary now signs every delivery twice: `X-Signature` (v1, over `{X-Timestamp}.{body}`, unchanged and deprecated) and the new `X-Signature-V2`, which also covers `X-Delivery-Id`, `X-Chronary-Event-Type`, `X-Chronary-Test` and `X-Chronary-Replay-Of`. Under v1 those headers were unsigned, so anyone holding a captured delivery could re-send it within the 5-minute tolerance under another event type (for example `event.hold_released` as `event.deleted`), with a fresh delivery id that got past deduplication, or with the test flag removed. `verify_signature()` and `unwrap()` (module functions and `client.webhooks.*`, sync and async) now check `X-Signature-V2` (or, during a secret rotation, `X-Signature-V2-Previous`) and never fall back to `X-Signature`: a delivery without `X-Signature-V2` raises `SignatureVerificationError`, as does one whose event type, delivery id, test flag or replay id differs from what was signed, an `X-Chronary-Test` other than `1`, or a header value containing CR or LF. Both also require `X-Delivery-Id` and `X-Chronary-Event-Type`. Every Chronary delivery carries the v2 headers, so a receiver needs no change beyond upgrading; test fixtures that sign deliveries by hand must add `X-Signature-V2` (see the webhooks API reference for the message format). Function signatures are unchanged.
- **`unwrap()` also returns `delivery_id`, `test` and `replay_of`** (`None` when the delivery is not a replay). They are covered by the signature, so deduplicate on `event["delivery_id"]`.
- **`verify_signature` and `unwrap` raise `SignatureVerificationError` for a non-ASCII signature header (#2724).** An `X-Signature` or `X-Signature-Previous` with non-ASCII characters (latin-1 bytes from WSGI / Starlette, lone surrogates from aiohttp) raised `TypeError` from `hmac.compare_digest`, so a receiver written as documented answered 500 instead of 401. The signatures are now compared as bytes. Applies to `chronary.verify_signature` / `unwrap` and `client.webhooks.verify_signature` / `unwrap` (sync and async). Real Chronary deliveries were never affected.
- **A refusal whose `Retry-After` is beyond 60 seconds is not retried (#2558).** The client clamped such a `Retry-After` to 60 s and retried, so an iCal manual-sync cooldown (429, up to 900 s on Free) or the anonymous sign-up daily cap (503, seconds to UTC midnight) blocked the call for about two minutes and then raised the same error. These now raise at once (delta-seconds or an HTTP date); a `Retry-After` of 60 s or less is still honoured and retried. Sync and async.
- **`auto_paging_iter()` follows `next_cursor` (#2691).** `agents.list()`, `calendars.list()`, `agents.calendars.list()` and `events.list_all()` paged by offset only, so iterating past 10,000 rows will fail once the API enforces its `offset` cap. They now page by the returned `next_cursor` (other lists still page by offset) and take a `cursor=` keyword. `ListResponse` and the pagers gain `next_cursor`, and `has_more` on those lists follows it. New helper `chronary.pagination.parse_list_response()`. Sync and async.
- **A custom `httpx_client` works (#2520).** A client passed as `httpx_client=` (the README's "Custom httpx client" example) was used as is, so requests carried no `Authorization` or `User-Agent` header (every authenticated call returned 401) and, with no `base_url` on the client, failed with `httpx.UnsupportedProtocol`. The SDK now adds its `Authorization`, `User-Agent` and `Accept` headers to every request unless your client already sets them, and prefixes its own `base_url` when the client has none (a `base_url` set on your client still wins). `timeout=`, which used to be ignored with a custom client, now applies to each request when you pass it; otherwise your client's own timeout is kept. Sync and async.
- `account.export()` returns the parsed DataExport `dict`, as annotated and documented, instead of the raw `httpx.Response` (#2556). Sync and async.
- **`agent_auth.sign_up_anonymous()` is no longer retried by default (#2690).** The server does not dedupe this POST, so after a lost response (a 5xx or a read timeout once the org was created) the default two retries could create up to three claimable organizations. Its `max_retries` now defaults to `0` (`None` also means 0); pass a number to opt back in. Sync and async.

## 0.13.3 — 2026-11-22

- `AuditActorType` gains `oauth_app`: an app the organization connected to the hosted MCP server by signing in, such as Claude. Its audit entries have `actor_id` set to the connection id and `actor_label` to the app's name, and `audit_log.list(actor_type="oauth_app")` filters by it. Sync and async (#2254).

## 0.13.2 — 2026-11-22

- **Path parameters are encoded (#2519).** Every ID a method puts into the URL path is now quoted as one segment (`urllib.parse.quote(safe="")`), so a value such as `../agents/agt_1`, `whk_1#` or `evt_1?expand=all` can no longer turn `events.delete_by_id()` or `events.get_by_id()` into a call on another resource or add a query string. `""`, `"."` and `".."` are refused before any request is sent with the new `InvalidPathParameterError` (a `ChronaryError` and a `ValueError`). Real Chronary IDs are unaffected. Sync and async.

## 0.13.1 — 2026-11-22

- `scheduling.respond()` returns `RespondToProposalResult` (a `ProposalResponse` subclass) with `auto_resolved` and `auto_resolve_error`. When the last response's auto-resolve fails, the API now answers 200 with `auto_resolve_error` (`code`, `message`) instead of an error status, because the response was saved; `message` says what to do next (usually `scheduling.resolve()`). Don't respond again. New exports `RespondToProposalResult`, `AutoResolveError` and `AutoResolveErrorCode`. Sync and async (#2540).

## 0.13.0 — 2026-11-17

- `client.agent_auth.sign_up_anonymous(agent_name=..., tos_version=..., source=None)` calls `POST /v1/agent/sign-up/anonymous`: a claimable organization with no email. Returns `AgentSignUpAnonymousResponse` with `api_key` (works at once, Sandbox limits), a one-time `claim_url` for the person who should own the calendar, and `expires_at` (72 hours; unclaimed, the org and its data are deleted). Sync and async (#2335).

## 0.12.0 — 2026-11-17

- `client.usage.get()` returns the new `calendar_connections` field (`ResourceUsage`, or `None` from a server that predates it): live Google / Microsoft calendar connections vs. the plan cap (#2397).
- Docstrings for `recurrence_rule`, the usage caps and the audit log name the Developer plan: Free 1 / Developer 50 / Pro 250 recurring series, with no end date required on Developer and Pro, and 30-day audit history on Developer. They previously said "Pro — 250 recurring events, unbounded allowed" and left out Developer (#2397).

## 0.11.1 — 2026-11-16

- README: the plans table gains the Developer plan. Developer now has every paid-plan feature, scheduling proposals (1,000 a month) and temporal holds included (#2331). No code change.

## 0.11.0 — 2026-11-16

- **Time-zone-aware recurrence (#2276).** `events.create` takes `timezone` (IANA, e.g. `"America/Los_Angeles"`), and `events.update` / `events.update_by_id` take it too (explicit `None` returns the series to UTC). A recurring series then repeats on local wall time: a weekly 16:00 stays 16:00 local across daylight-saving changes, and BYDAY, the `start_time` match and a date-only UNTIL are read in that zone. `timezone`, `recurrence_rule` and `start_time` sent together are validated once, on the merged result. `Event` gains `timezone`, and expanded instances (`expand=True`) gain `start_local`, `utc_offset` and `dst_adjusted` (`"gap"` when a local time skipped by a DST gap was moved forward).
- **Series edits keep cancelled occurrences (#2277).** An update that changes `start_time`, `recurrence_rule` or `timezone` on a recurring series carries each cancelled occurrence (exdate) to the new occurrence on the same local date instead of clearing it. Any with no occurrence on that date are removed and returned in the new `Event.dropped_exdates`; re-cancel with `delete(occurrence_start=...)` if needed. Clearing the rule still clears them.

## 0.10.0

- `UsageResponse` gains the two fields the API already returned: `webhook_endpoints` (`ResourceUsage`: registered webhook endpoints vs. the plan cap) and `scoped_keys` (new `ScopedKeysUsage` with `count` and `limit`: active agent-scoped keys). A new test fails when the API's `Usage` response gains a field the model lacks (#1995).

## 0.9.0

- A 429 `quota_exceeded` (a monthly plan limit) is no longer retried: the client raises `QuotaExceededError` at once instead of sleeping and asking again. A rate-limit 429 still retries, honouring `Retry-After` up to 60 seconds (#1936).
- Cap a server-supplied `Retry-After` at 60 seconds, like the TypeScript SDK. A monthly quota 429 sends the seconds left in the month, so a client that hit its cap used to sleep until the month ended instead of raising `QuotaExceededError`.
- Add the `developer` plan: `PlanId` accepts it (and any later plan id as a plain string), `Plan.annual_price`, `BillingSummary.pending_plan` / `pending_plan_interval` / `pending_plan_at`, `BillingUpgradeOption.via`. API status errors expose `upgrade_plan`. Additive (#1911).

## 0.8.1 — 2026-11-09

- `client.waitlist.join()` now returns `WaitlistJoinResponse(waitlisted=True, message=...)` (HTTP 202) for every email, whether new, already on the list or with an active account. It no longer returns the entry (`data`) and no longer raises 409 `email_taken`. `join()` takes `intent`; `WaitlistedOrg` is deprecated (#1655).

## 0.8.0 — 2026-10-19

- Add `client.billing.get()` and `client.billing.upgrade_requests.create/get/cancel` (sync and async) so an agent can read plan status and ask its human to upgrade (#1129).
- Add `PlanRequiredError` (a `PermissionDeniedError` for 403 `plan_required`). `APIStatusError` now exposes `upgrade_url`, `docs_url`, `required_plan`, `feature`, `contact_url`, `metric` and `limit`.
- Add the `org.plan_changed` webhook event type: fires once when the account's plan changes, so agents don't have to poll billing (#1130).
- Add the `calendar_connection.reauthorization_required` webhook event type: fires once when a connected human calendar stops accepting access, so agents learn their availability now fails closed (#1196).
- Add `client.connection_links.list(status=, calendar_id=, limit=)` (sync and async) and the setup details on `ConnectionLink` (`requesting_agent_id`, `requested_capabilities`, `requested_publication_policy`, `created_at`) (#1196).
- `client.webhooks.list_deliveries()` takes `event_type` (exact, or a prefix ending in a dot such as `event.`), `created_after`, `created_before`, `delivery_id`, `is_test` and `cursor`, and the response gains `next_cursor` and `has_more`. `DeliveryStatus` gains `dropped` (a Free-plan delivery the monthly limit stopped), and `WebhookDeliveryStats` gains `dropped` (#1200).
- Add `client.webhooks.get_delivery(webhook_id, delivery_id)` (sync and async): one delivery with its attempt timeline (`attempt_log`: HTTP status, duration, response body prefix, error code). `WebhookDelivery` gains `last_response_status`, `last_error_code` and `last_duration_ms` (#1200).
- Add `client.webhooks.send_test(webhook_id, event_type=...)` (sync and async): sends a signed sample payload once (`is_test`, `X-Chronary-Test: 1`, quota-exempt). Deliveries gain `is_test`, and `Webhook` gains `deactivated_at` and `deactivated_reason` (#1200).
- Add `client.events.list_all(calendar_id=, agent_id=, start_after=, start_before=, status=, source=, q=, expand=)` (sync and async): events across all of the organization's calendars (`GET /v1/events`); `calendar_id` takes one id or a list. Add `client.calendars.rotate_ical_token(calendar_id)` to regenerate a calendar's subscribe URL, and `q` on `client.calendars.list()` (#1202).
- Add `client.booking_pages.list_bookings(booking_page_id, limit=, cursor=)` (sync and async): the bookings made through a page with the invitee's name, email and notes, newest first, paged by `next_cursor`. Add `client.booking_pages.rotate_slug(booking_page_id)` to replace a page's public link, and `calendar_id` on `client.booking_pages.list()` (#1202).
- Add `client.webhooks.replay_delivery(webhook_id, delivery_id)` (sync and async, Pro): sends a `failed` or `dropped` delivery again as a new delivery, with an `X-Chronary-Replay-Of` header naming the original. It counts toward the monthly delivery quota. Add `WebhookReplaySent`. `WebhookDelivery` gains `replay_of_delivery_id` (#588).
- **Webhook secret rotation (#594).** `verify_signature` and `unwrap` now accept a delivery when the secret matches either `X-Signature` or `X-Signature-Previous`. During a rotation's grace window Chronary sends both headers, the second signed with the replaced secret, so a receiver can switch secrets without rejecting deliveries. Update before you rotate a secret. Add `client.webhooks.rotate_secret(webhook_id, expire_old_in=...)` (sync and async, Pro): returns the new secret once (`RotatedWebhookSecret`), and the old one keeps working for `"now"`, `"1h"`, `"24h"` (default) or `"7d"`. `Webhook` gains `previous_secret_expires_at`.

## 0.7.1 — 2026-07-14

- Add the `booking_pages` field to `UsageResponse` (it was omitted). Neutral wording for the booking-page resource docstring.

## 0.7.0 — 2026-07-14

- Add the `booking_pages` resource (sync + async CRUD) for agent-created public scheduling links (#1036).

## 0.6.0 — 2026-07-12

- Add sync and async `allow_stale` support plus typed availability completeness, source health, and warnings.

## 0.5.1 — 2026-07-12

- Add connection-link APIs so agents can request and monitor human calendar setup without receiving provider credentials or calendar details.

## 0.5.0 — 2026-07-10

- Recurring events (#996):
  - `events.create` accepts `recurrence_rule` (RFC 5545 RRULE subset, no `RRULE:` prefix, e.g. `FREQ=WEEKLY;BYDAY=MO,WE;COUNT=12`). Not allowed with `status="hold"`. Free plan: 5 recurring events, series must end within 90 days (bounded COUNT/UNTIL); Pro: 250, unbounded allowed.
  - `events.update` / `events.update_by_id` accept `recurrence_rule` as a full-series edit; passing `None` explicitly clears the rule.
  - `events.list` and `agents.events.list` accept `expand=True` to expand recurring masters into instances (requires `start_after` + `start_before`, max 366 days apart).
  - `events.delete` / `events.delete_by_id` accept `occurrence_start` (ISO datetime) to cancel a single occurrence; they then return the updated series master `Event` instead of `None`.
  - `Event` model gains `recurrence_rule`, `recurrence_exdates`, and (on expanded instances) `recurring_event_id` / `original_start_time`.
  - `UsageResponse` gains `recurring_events` (`used` / `limit`).

## 0.1.3 — 2026-05-18

- First publish to pypi.org as `chronary` with PyPI Trusted Publishing (OIDC) and Sigstore attestations. Prior releases were source distributions on `Chronary/chronary-python` Releases only, installable via `pip install git+https://github.com/Chronary/chronary-python.git@vX.Y.Z`.

## 0.1.2 — 2026-05-18

- Add `CONTRIBUTING.md` to the public mirror documenting that this repo is generated from a private monorepo; PRs are welcome as proof-of-concept but can't be merged directly. No behavioral change.
