# ASMT-007: Advance and reject actions

| Field | Value |
|---|---|
| Epic | ASMT — Assessment & review |
| Milestone | M5 Review |
| Status | Done |
| Size | M |
| Depends on | [PIPE-008](../PIPE/PIPE-008-pipeline-details-candidates-tab.md), [MSG-003](../MSG/MSG-003-email-scheduling-and-sending-engine.md) |
| Requirements | FR-PIPE-13 |
| Gap areas | G5, G6 |
| Design | Frame PipelineView (reject dialog) + A-02 |
| Docs to read | [`decisions/ADR-017-manual-advance-action.md`](../../decisions/ADR-017-manual-advance-action.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users move candidates forward or reject them with a reason, and candidates are told.

## Scope
**In:**
- Reject dialog (reason required, email option)
- Advance dialog (note, email option)
- Endpoints with permission + stage rules
- Emails: next_stage / reject_* chosen by stage

**Out:**
- —

## Acceptance criteria
- [x] Rejected/advanced are terminal
- [x] Scheduled automatic emails cancelled when a TA acts
- [x] HM cannot act
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Advance needs every integrity flag reviewed (A-02, FR-PIPE-13): refuse it while `applications.has_open_flags` is true; ASMT-003 clears the overlay when the last flag is reviewed (`PATCH /v1/integrity-flags/{id}`). The web already hides or disables Advance while `flagged`.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
Plan auto-approved (owner's standing rule: no plan approvals).

**API** (`services/decisions.py`, routes in `api/routers/applications.py`, `decide_candidates`: Admins any pipeline, Recruiters their departments, Hiring managers `403`; another workspace, department or deleted candidate data is `404`):
- `POST /v1/applications/{id}/advance {note?, send_email}`: only from `ready_for_review` with no open flags (`409 decision_not_allowed`, `409 flags_to_review`). Sets `advanced_note`/`advanced_by`/`advanced_at`, moves the stage with `applications.move_stage()` (which cancels waiting emails), then, when ticked, schedules `next_stage` now.
- `POST /v1/applications/{id}/reject {reason, send_email}`: reason required (1–500 characters, trimmed). From `invited`, `interview_in_progress`, `ready_for_review` (flagged or not), and `processing_resume` with an unreadable résumé (WORKFLOW.md §3; SCREEN-004 adds the menu entry). A running interview attempt is ended and its call hung up after the commit; the link then shows "no longer available". Email: `reject_interview` after a finished interview, otherwise `reject_resume` (NOTIFICATIONS.md §1), sent now, with a `[Review.link]` like every rejection (the renderer always adds the review line; an existing link of that type gets a new token).
- Both lock the application (the live interview first, the order an attempt takes them), refuse a terminal or other stage, write `audit_log` (`application.advanced` / `application.rejected`, stage and whether emailed; never the note or reason), commit, then enqueue the email. Response `{id, stage, emailed}`.
- Profile journey: the advanced/rejected step carries who and the note or reason (team only).

**Web**: `AdvanceDialog` and `RejectDialog` (`components/candidates/decision-dialogs.tsx`, rules in `lib/candidates/decisions.ts`) with A-02 and frame PipelineView copy; opened from the Candidates tab row menu and the profile header and phone bar; on success a toast, and the profile and Candidates tab re-read. A `409` closes nothing and says why.

**Tests**: service tests for stages, flags, emails (template choice, untick, cancelled automatic emails), mid-interview reject, terminal states; tenancy and role tests for the two endpoints; web unit tests for the dialog rules.

## Log
- Branch `feature/asmt-007-0j52c0`, PR #57. Plan auto-approved (owner's standing rule).
- Default picked, not asked: a TA rejection email carries the "Request a human review" line like every rejection (the renderer always adds it, NOTIFICATIONS.md §2), with a `review_links` row of the matching decision type. ASMT-008 decides how a request on a person's rejection is handled.
- Rejecting an unreadable résumé (`processing_resume` + `resume_status = unreadable`) is allowed by the API now; SCREEN-004 adds the badge and the menu entry.
- `advanced_by`/`rejected_by` hold the workspace member ID (their FK); the profile journey shows the member's name and the note or reason.
- Rejecting mid-interview ends the running attempt (`disconnect`), so the interview reads abandoned; its "Finish your interview" email is cancelled with the stage change.
- Hand-tested on the Acme Talent seed at 360, 768, 1024 (dark) and 1440: advance from the row menu, reject from the profile with the reason error, the phone sheets, unticked email, Hiring manager without actions.
- Board: ASMT-007 Done; ASMT-008 Ready. REL-001 still waits on BILL-005.
