# MSG-003: Email scheduling and sending engine

| Field | Value |
|---|---|
| Epic | MSG — Candidate emails |
| Milestone | M3 Intake |
| Status | Done |
| Size | M |
| Depends on | [MSG-001](../MSG/MSG-001-email-templates-model-and-defaults.md), [FND-008](../FND/FND-008-background-worker-and-job-framework.md) |
| Requirements | FR-MSG-04, FR-MSG-05, FR-MSG-06 |
| Gap areas | G1, G5 |
| Design | — |
| Docs to read | [`architecture/NOTIFICATIONS.md`](../../architecture/NOTIFICATIONS.md), [`product/WORKFLOW.md §5`](../../product/WORKFLOW.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Candidate emails go out at the right moment in the workspace's time zone and never contradict the candidate's current status.

## Scope
**In:**
- Business-day calculator (workspace tz)
- `schedule(template_key, application, at)` + cancel rules on stage change
- `dispatch_scheduled_emails` cron
- Bounce handling marks candidate email undeliverable

**Out:**
- —

## Acceptance criteria
- [x] Rejection after override is cancelled
- [x] Friday screening → Tuesday email (2 business days)
- [x] Idempotent: no duplicates on retries
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint (none: no new endpoints)
- `tests/unit/test_business_days.py`: Friday → Tuesday, counting in the workspace zone, weekend starts, daylight saving, unknown zones, expiry wording, name split
- `tests/integration/test_candidate_emails.py`: scheduled rejection waits for its time then sends with the candidate's values and review link; scheduling twice keeps one email; override cancels the rejection (`move_stage()`), the send job cancels one whose stage moved without it; a missing `Review.link` is refused; hard bounce marks the candidate, soft doesn't
- `tests/integration/test_emails.py`: the dispatch cron re-queues a due email Redis lost

## Implementation plan
Auto-approved (the owner asked for no plan approval stops).

1. **Migration** `email_scheduling`: `email_messages.application_stage` (the stage the email was written for) and `dedupe_key` (unique while the email isn't cancelled); `candidates.email_undeliverable_at`.
2. **Business days** (`app/core/business_days.py`): `add_business_days(start, days, zone)` skips Saturday and Sunday in the workspace time zone and keeps the local time of day (Friday 10:00 + 2 → Tuesday 10:00; a weekend start counts from Monday); `zone_of()` falls back to UTC for an unknown zone; `format_local()` writes `[Interview.expiry]` as "Fri, 3 Oct 2026, 11:59 PM PST".
3. **Scheduling** (`app/services/candidate_emails.py`): `schedule(session, workspace_id, application_id, key, at=None, values=None, dedupe_key=None)` reads the workspace's template, the candidate, the pipeline title and the company branding, renders through `render_template()` and stores the email with the application's current stage. The caller passes the values only it knows (`Interview.link`, `Interview.expiry`, `Review.link`). The default dedupe key is `{key}:{application}:{stage}`, so a retried job never queues a second copy (`created: false`). `send_at(session, workspace_id, start, business_days)` gives the time for a business-day delay. Pipeline toggles stay with the callers (SCREEN-003, INTV-007, ASMT-007).
4. **Cancel rules**: `services/applications.move_stage()` is the one way to change an application's stage from here on; it cancels the application's scheduled emails (`cancel_reason = stage_changed`) in the same transaction. As a safety net, the send job won't claim an email whose application has moved on from `application_stage`; it cancels it instead.
5. **Dispatch**: `emails.enqueue()` queues only emails already due; the new every-minute cron `dispatch_scheduled_emails` queues every due `scheduled` email (keyed by ID, so a repeat is a no-op). It replaces the email part of `requeue_stuck_work`.
6. **Bounces**: a Resend `email.bounced` event that is a hard bounce (type `Permanent`, or no type) sets `candidates.email_undeliverable_at` for the candidate the email went to, while the candidate still has that address; a new address on a later application clears it.
7. **Tests**: unit tests for business days and expiry formatting; integration tests for scheduling and dedupe, Friday → Tuesday, cancellation after an override (both `move_stage()` and the send-time guard), dispatch of due emails only, and bounce marking.
8. **Docs**: NOTIFICATIONS.md, DATABASE.md, BACKEND.md crons, AGENTS.md status, BOARD.md.

## Log
- Branch `feature/msg-003-email-sending-dokcet`. Plan auto-approved per the owner's rule.
- Decisions (defaults, open to change): rendered when scheduled (as FND-010 designed), so a template edit after scheduling doesn't change an email already waiting; the delay keeps the local time of day rather than moving to business hours; candidate first name is the first word of the full name and last name the last word.
- Tested by hand: three applications through the real worker into Mailpit. The rejection and the invitation arrived as "{Company} via FastHyr" with the candidate's name, the job title and the review or interview link; the rejection overridden to `invited` was cancelled and never sent. Screenshots in the PR.
- `requeue_stuck_work` no longer re-queues emails; `dispatch_scheduled_emails` covers due emails every minute. `[Interview.expiry]` uses tzdata's abbreviation, so Manila reads "PST" (Philippine Standard Time), not "PHT" as NOTIFICATIONS.md's old example said.
