# SCREEN-003: Post-screen actions: invite or schedule rejection

| Field | Value |
|---|---|
| Epic | SCREEN — Résumé screening |
| Milestone | M3 Intake |
| Status | Done |
| Size | M |
| Depends on | [SCREEN-002](../SCREEN/SCREEN-002-resume-assessment-and-decision.md), [MSG-003](../MSG/MSG-003-email-scheduling-and-sending-engine.md), [INTV-001](../INTV/INTV-001-interview-plan-generation.md) |
| Requirements | FR-SCREEN-05 |
| Gap areas | G1, G5 |
| Design | — |
| Docs to read | [`product/WORKFLOW.md §3`](../../product/WORKFLOW.md), [`architecture/NOTIFICATIONS.md`](../../architecture/NOTIFICATIONS.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Passing candidates are invited to interview automatically; others get a kind rejection with a review route at the right time.

## Scope
**In:**
- On pass: plan interview → create interview (token, expiry) → invitation email
- On fail: stage `resume_not_match`, schedule `reject_resume` (2 business days) if enabled, with review link
- Stage polling visible in UI

**Out:**
- —

## Acceptance criteria
- [x] Invitation contains a working personal link
- [x] Rejection email includes `[Review.link]`
- [x] Toggle off → no email
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
1. **Migration** `20261003210000_interviews_and_review_links.sql`:
   - `interviews` with every DATABASE.md column (INTV-002 and later tasks fill the rest). `token_hash` unique; one live interview per application (unique on `application_id` where `superseded_by` is null); index `(status, expires_at)` for INTV-007's cron. RLS on, no grants to the public keys.
   - `review_links`: the "Request a human review" link of an automated rejection (ADR-015): `application_id`, `decision_type` (`resume|interview`), unique `token_hash`, `expires_at` (30 days after the email goes out), one per application and decision type. ASMT-008's `human_review_requests` points at it instead of holding its own token.
2. **`services/post_screen.act()`**, idempotent, run after every screen and plan: does nothing unless the application is in `processing_resume` with `resume_status = done`.
   - Failed screen → `move_stage(resume_not_match)`; when the pipeline's "Email candidates whose résumé isn't a match" is on, a review link and `reject_resume` scheduled 2 business days after `screened_at` (`candidate_emails.send_at()`).
   - Passed screen with its interview plan → `move_stage(invited)`, an `interviews` row (format from the pipeline, `not_started`, token hash) and `interview_invitation` now with `[Interview.link]` = `{SITE_URL}/interview/{token}` and `[Interview.expiry]`.
   - Passed without a plan yet → waits; `plan_interview` acts once the plan exists.
   - `move_stage()` locks the application row, so a second run that lost the race rolls back.
3. **Jobs**: `screen_resume` and `plan_interview` call `act()` after their step (also when the step was already done, so a retry finishes the work); the plan job's fallback hook acts too (its email goes out with the next `dispatch_scheduled_emails` tick). `requeue_stuck_work` also re-queues screened applications still in `processing_resume` 10 minutes after `screened_at` (failed → `screen_resume`, passed with a plan → `plan_interview`).
4. **Link expiry**: the end of the day (23:59:59) in the workspace time zone, `link_expiry_days` after the invitation (`end_of_day_after()` in `app/core/business_days.py`), so `[Interview.expiry]` reads "…, 11:59 PM PST".
5. **Stage polling in the UI**: the apply page re-reads `my-application` every 15 s while the status is "Your application is in" (stops after 10 minutes or when the tab is hidden), so the notice turns into "Your AI interview is ready" or "with {company}" without a reload.
6. **Tests** (after hand-testing in the worker): pass → invited with one interview, a personal link whose hash matches, and an invitation sent; fail → `resume_not_match`, `reject_resume` scheduled 2 business days later with the review link; toggle off → no email; a repeat run changes nothing; the sweeper finishes a screen whose action was lost; `end_of_day_after()` unit test.
7. **Docs**: DATABASE.md (`interviews` note, `review_links`), BACKEND/AI_PIPELINE where the stage move is described, INTV-002 and ASMT-008 task notes, AGENTS.md status, BOARD.md (SCREEN-003 Done; INTV-002 waits on nothing else → Ready).

Defaults picked (not confirmed by the product owner): the link stays open to the end of its last day in the workspace time zone; the review link lasts 30 days from the email's send time; a pipeline closed after someone applied still invites them (they used a credit).

## Log
- Branch `feature/screen-003-invite-or-reject-vdwf1v`, PR #41.
- 2026-10-03: plan auto-approved (owner's standing rule). Built as planned.
- Hand test (local, `AI_FAKE=1`, seeded Acme Talent): a candidate applied with the worker stopped; the apply page showed "Your application is in", then switched to "Your AI interview is ready" 14 s after the worker started, without a reload (360 and 1440 px). The invitation reached Mailpit with `/interview/{token}` and "Fri, 9 Oct 2026, 11:59 PM PST". A screen failed by raising the pass bar to 100 landed in `resume_not_match` with `reject_resume` scheduled for the next business days at the same local time and a review link valid 30 days after it. Screenshots: `screenshots/SCREEN-003/` in the project files.
- `services/applications.py` imports the screening job and the jobs now import `post_screen`, so `post_screen._move()` imports `move_stage` inside the function to break the cycle.
- The `interviews` table is created here with every DATABASE.md column so INTV-002 starts from it; `review_links` is new (DATABASE.md), and ASMT-008's `human_review_requests` points at it.
- Board: SCREEN-003 Done; INTV-002 Ready (its other dependency, APPLY-002, is Done). SCREEN-004 still waits on PIPE-008 and ASMT-008 on ASMT-007.
