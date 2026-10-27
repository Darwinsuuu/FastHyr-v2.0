# PIPE-005: Pipeline lifecycle actions

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M2 Pipelines |
| Status | Done |
| Size | M |
| Depends on | [PIPE-004](../PIPE/PIPE-004-pipelines-list.md), [FND-010](../FND/FND-010-email-infrastructure-resend.md) |
| Requirements | FR-PIPE-07 |
| Gap areas | G5 |
| Design | Frame PipelinesV2 (modals) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users pause, resume, close, cancel, archive, start now and duplicate pipelines from the list and detail header.

## Scope
**In:**
- Pause, close (with Role closed email option), cancel, archive dialogs as designed
- Resume, start now, duplicate as new draft
- Top-up entry point → BILL-006 modal

**Out:**
- —

## Acceptance criteria
- [x] Each action matches its dialog copy and resulting state
- [x] Close with notify queues `role_closed` emails to candidates without a final outcome
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Until MSG-001 lands, the role-closed email uses the default template file shipped with the API

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
Plan auto-approved (owner's standing rule: no plan approvals).

PIPE-001 already built the state machine and every lifecycle route, so this task is mostly the web, plus the close email.

1. **API: close with notify.** `POST /v1/pipelines/{id}/close` takes an optional body `{notify: bool}` (default false, so old callers keep working). With `notify`, `services/pipelines.close()` schedules `role_closed` for each application that hasn't heard back, in the same transaction as the close, then enqueues them after commit (like "Re-invite all"). The response is the pipeline plus `notified` (how many emails). Audit `pipeline.closed` gains `notified`.
   **"Haven't heard back"** (the dialog's words; NOTIFICATIONS.md "no final outcome email") means the candidate has nothing more coming from the pipeline unless the team acts, and no outcome email sent or waiting:
   - Ready for review (waiting on the team);
   - Didn't pass or résumé not a match, when no rejection email was sent or is waiting (the pipeline's toggle was off);
   - Invited with an interview link that has expired (`interviews.status = expired`);
   - Résumé unreadable or failed to process (`resume_status` `unreadable` / `error`).
   Left out: anyone still able to go on (résumé being screened, a live interview link, mid-interview, being scored, since closing lets them finish), advanced and rejected (the team decided, including choosing not to email), anyone with a `next_stage`, `reject_resume`, `reject_interview`, `review_upheld` or `role_closed` email that isn't cancelled or failed, deleted candidates. The stage doesn't change: everyone stays in the pipeline with their results. Dedupe key `role_closed:{application}`.
2. **Web, shared:** `lib/pipelines/actions.ts` (which dialog or call each action is, the copy values, the API call per action) and `components/pipelines/pipeline-actions.tsx` with `usePipelineActions()`: Pause, Close (checkbox, ticked by default), Cancel, Archive dialogs as in frame PipelinesV2 on the kit `ConfirmDialog`; Start now also confirms (it locks the setup and can't be undone; not in the frame); Resume runs at once; Duplicate makes the draft and opens its wizard. Success shows a toast and refreshes the list, the pipeline, the dashboard and the credit summary; a `409` shows its message in the dialog.
3. **Pipelines list:** the row menu entries become live (Copy apply link waits for PIPE-006 and Top up for BILL-006, both stay disabled). Closed and cancelled rows also get "Duplicate as new pipeline" (the frame's Setup tab offers it; on the list it's the quickest way to reopen a role).
4. **Pipeline details header:** a "More actions" menu next to Share apply link with the same entries for the status (minus Open) plus Duplicate; archiving from there goes back to `/pipelines`.
5. **Tests:** API: close with notify emails exactly the right applications and enqueues them, without notify sends nothing, 409 on a closed pipeline; tenancy (another workspace's pipeline is 404). Web unit: menus per status and role, dialog values. Playwright: close with notify from the list.
6. Docs: API.md, NOTIFICATIONS.md, AGENTS.md status, BOARD.md (PIPE-005 Done).

## Log
- Branch `feature/pipe-005-taxpj5`. Plan auto-approved per the owner's rule.
- "Haven't heard back" read as in the plan (nothing more coming unless the team acts, and no outcome email sent or waiting). On the seed's Senior Backend Engineer that's 104 of 142, mostly Didn't pass / not a match, because the seed has no rejection emails; with the rejection toggles on (the default) those candidates are left out.
- Deviations from the frame: Start now asks first (it locks the setup); "Duplicate as new pipeline" is also on closed and cancelled rows of the list and in the details header's "More actions" menu (the frame has it on the Setup tab, PIPE-009). Top up stays disabled (billing goes last).
- Hand-tested at 360, 768, 1024 and 1440 px against the seed: pause, resume, close with notify (Mailpit received the emails), cancel, start now, archive and duplicate from the list, and the header menu.
- The "Role closed" template comes from MSG-001, so the note about a default file shipped with the API no longer applies.
