# Changelog

All notable changes to `chronary` (Python SDK) will be documented in this file starting with the soft-launch release.

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
