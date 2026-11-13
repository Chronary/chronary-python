# Changelog

All notable changes to `chronary` (Python SDK) will be documented in this file starting with the soft-launch release.

## 0.9.0 — Unreleased

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
