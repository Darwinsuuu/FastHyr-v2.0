# INTV-007: Interview lifecycle: resume, expiry, reminders, re-invite, drop-off reasons

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M4 AI interview |
| Status | Done |
| Size | M |
| Depends on | [INTV-005](../INTV/INTV-005-live-interview-ui-client.md), [MSG-003](../MSG/MSG-003-email-scheduling-and-sending-engine.md) |
| Requirements | FR-INTV-06, FR-INTV-08, FR-PIPE-11 |
| Gap areas | G1 |
| Design | Frames PipelineView (drop-offs), EmailTemplates |
| Docs to read | [`product/WORKFLOW.md §4–5`](../../product/WORKFLOW.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Candidates who don't start or finish are nudged, can resume, and TA teams see why and can re-invite.

## Scope
**In:**
- Abandon detection (missed heartbeats)
- Cron: expire links, send reminders, nudge unfinished
- Drop reason codes
- Re-invite API (single + all unfinished)
- Talk-time cap across attempts

**Out:**
- —

## Acceptance criteria
- [x] Reminder only if pipeline toggle on and not started
- [x] Re-invite supersedes old link
- [x] Drop-off counts appear in analytics (data in `v_dropoff_reasons`; the Overview and pipeline dashboard cards that show it are DASH-003 and PIPE-007)
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md)): not applicable, no screen in this task ("Re-invite all" is PIPE-007's button)
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- The link page (INTV-002) already shows `expired` once `expires_at` passes and `unavailable` for a link with `superseded_by` set, so a re-invite only needs to set `superseded_by` on the old row.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Auto-approved per the owner's standing rule: no plan approvals.)_

Already in place from INTV-004: resume while the link is valid, the 30-minute cap across attempts (`seconds_allowed`), abandon detection by missed heartbeats (the `end_overdue_attempts` watchdog ends an attempt after 60 s of silence and leaves the interview `abandoned`). This task adds what happens around that.

The interview link token is only ever stored hashed, so emails that carry the link must be written while the token is in hand:
- **Reminder** (`interview_reminder`): scheduled with the invitation at `expires_at − 24 h` when the pipeline's `reminder_enabled` is on (dedupe `interview_reminder:{interview_id}`). Starting the interview moves the stage to `interview_in_progress`, which already cancels it (MSG-003). `reminder_sent_at` is set by the send job when it goes out.
- **Finish your interview** (`finish_interview`): written when an attempt starts (the candidate's request carries the token) as a **held** email (new `email_messages.status = 'held'`, never dispatched). When an attempt ends and leaves the interview `abandoned`, the held email is scheduled for 1 h later, or cancelled if the link closes before then. A new attempt puts a not-yet-sent one back on hold. Completing moves the stage, which cancels it. Once sent it is never written again (dedupe `finish_interview:{interview_id}`), so it goes at most once per link.

Drop reasons (`interviews.drop_reason`) say why a live, unfinished interview isn't done:
- `left_unfinished`: set when an attempt ends and leaves the interview `abandoned`; cleared when a new attempt starts.
- `technical_issue`: as INTV-004 (three failed connects), kept through expiry.
- `link_expired`: set by the new `expire_interview_links` cron (every 10 minutes) on `not_started` links past `expires_at` with no other reason.
- The cron moves `not_started` and `abandoned` live links past `expires_at` to `status = expired` and cancels their waiting emails. A running attempt is never expired; the watchdog ends it, then the next run expires it.
- Completing clears the reason.

Re-invite (`services/interview_lifecycle.py`, permission `decide_candidates`, Recruiters only in their departments):
- `POST /v1/applications/{id}/reinvite` → one application; `POST /v1/pipelines/{id}/reinvite {scope: "all_unfinished"}` → every application whose live interview is expired, abandoned, past its expiry, or stuck on a technical issue.
- Eligible: stage `invited` or `interview_in_progress`, live interview not `completed` and no attempt running, pipeline not cancelled or archived. Otherwise `409 reinvite_not_allowed`.
- Creates a new `interviews` row (new token, fresh expiry and 30 minutes, same plan, same credit) and sets the old row's `superseded_by` (the link page then shows "unavailable"); the FK becomes deferrable so both happen in one transaction. Stage goes back to `invited`; the application's waiting emails are cancelled; a new invitation (and reminder) is scheduled with dedupe keys per interview. Audit `application.reinvited`.
- Invitation creation moves from `post_screen._invite()` into the shared `interview_lifecycle.issue_link()`.

Analytics: SQL view `v_dropoff_reasons` (security invoker) with one row per live unfinished interview that has a drop reason (workspace, pipeline, department, application, interview, reason, `dropped_at`). DASH-003 and PIPE-007 read it for Overview and the pipeline dashboard; this task has no screen of its own (the "Re-invite all" button comes with PIPE-007), so the responsive check doesn't apply.

Tests: expiry cron (reasons, running attempt untouched), finish email held → scheduled → re-held → cancelled, reminder scheduled only with the toggle, re-invite supersedes the old link and sends a new invitation, bulk scope, `409` cases, tenancy and department scope for both routes.

## Log
- 2026-10-05: branch `feature/intv-007-interview-lifecycle`; plan auto-approved (owner's standing rule).
- PR #47.
- Everything lives in `services/interview_lifecycle.py` (links and their emails, finish email, expiry, re-invites) rather than a separate re-invite module.
- Hand test (local stack, `AI_FAKE=1`): applied as a Google candidate → invited with the invitation sent and the reminder scheduled for 24 h before 11:59 PM Manila; made the reminder due → sent to Mailpit and `reminder_sent_at` set; expired the link → `expired`/`link_expired` and a `v_dropoff_reasons` row; `POST /v1/applications/{id}/reinvite` as Dana → new invitation in Mailpit, old link `unavailable`, new link opens; "Re-invite all" then found nobody left. The finish email (needs a live attempt) is covered by the integration tests with the fake Realtime provider.
