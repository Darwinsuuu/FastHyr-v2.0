# APPLY-004: Apply edge cases and states

| Field | Value |
|---|---|
| Epic | APPLY — Apply |
| Milestone | M3 Intake |
| Status | In review |
| Size | S |
| Depends on | [APPLY-003](../APPLY/APPLY-003-application-submission-and-credit-use.md) |
| Requirements | FR-APPLY-05, FR-APPLY-06, FR-APPLY-07 |
| Gap areas | G1 |
| Design | Frame Apply |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Every unusual situation on the apply page has a clear, kind message.

## Scope
**In:**
- Already applied (shows status text)
- Pipeline paused/closed between page load and submit
- Upload failures and retry
- Large/invalid PDF messages
- Signed in as a TA member of the same workspace (allowed, warned)

**Out:**
- —

## Acceptance criteria
- [x] No credit used on any failed submit
- [x] Messages follow VOICE_AND_TONE
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Auto-approved per the owner's standing rule: plans are written here and built without a separate approval.)_

**Already applied: status text** (FR-APPLY-05, FR-APPLY-07)
- `GET /candidate/pipelines/{id}/my-application` adds `status`, a candidate-safe word for the stage, never the stage itself: `received` (processing_resume), `interview` (invited, interview_in_progress), `with_team` (every later stage, including the "not moving forward" ones, so the page never gets ahead of the emails WORKFLOW.md §3 sends, some of them days later). Null when not applied.
- The page's "Your application is in" notice follows it: résumé being reviewed, interview link emailed, or with the company's team with updates by email. A second Send (another tab) lands on the same state with no credit (APPLY-003 already returns `created: false`).

**Pipeline paused or closed between page load and submit** (FR-APPLY-06)
- The API already refuses with `409 pipeline_not_accepting` at the upload URL and at submit, before any credit or file moves. New test: upload while live, the pipeline pauses (or closes), then submit: 409, no credit, no application, no stored résumé.
- The form keeps the candidate's details, says why in the footer using the pipeline's new state (closed, or not taking applications right now), and refreshes the page in the background (`router.refresh()`) so the banner and both Apply buttons show the new state. If the role reopens, Send works again without a reload.

**Upload failures and retry**
- The PUT to the signed URL gets one quiet retry on a network error or 5xx; then the résumé field says it didn't upload and Send starts again from a new upload URL. A network error on our own API says we couldn't reach FastHyr and the details are still here, instead of the generic line. A 413 from Storage reads as the 10 MB message.

**Large or invalid PDFs, before anything is sent**
- `FileDrop` gets an optional `check` (sync or async) that replaces its generic type and size check. The form's `checkResume()` (`lib/apply/form.ts`): empty file, over 10 MB, not a PDF by type or name (some phones and Windows give PDFs no MIME type, so a `.pdf` name with an empty or generic type is accepted), and the first bytes must be `%PDF-`. Messages are the résumé-specific ones the server's codes already map to, plus one for an empty file.

**Signed in as a TA member of the same workspace** (allowed, warned)
- `my-application` adds `workspace_member` (the account has an active membership in the pipeline's workspace; only the caller's own row is read). The form shows a notice above the résumé: they can still apply, it's handled like any other application, and their teammates will see it. Nothing is blocked.

**Tests** (after it works): API: the paused/closed race uses no credit; `my-application` status mapping and `workspace_member`. Web: `checkResume()`, `submitProblem()` for network, 413 and closed vs paused, the status text choice.

**Docs**: API.md (my-application fields), AGENTS.md current status, BOARD (APPLY-003 Done, APPLY-004 In review, newly unblocked tasks Ready).

## Log
- 2026-10-02: branch `feature/apply-edge-cases-1pvxm1` from `develop`. Plan auto-approved (owner's standing rule).
- Decisions: the candidate sees three status words, never the stage; "with the team" covers every decision too, so the page never announces a result before the (sometimes delayed) email. TA members signed in with Google or Microsoft may apply and get a note in the form; nothing is blocked. A 404 at submit (role taken down) shows the closed message without refreshing the page into "not found".
- Hand-tested on local Supabase with Google-style accounts: member note (light 360/1440, dark 1024); non-PDF and empty files refused before upload; storage upload blocked (two tries, then the résumé message) and API unreachable (connection message), with no credit used; pipeline paused and closed after the form opened (no credit used, page behind updates, Send works again after it reopens); status text for received, interview and with the team at 360/768/1440. Screenshots in the project files under `screenshots/APPLY-004/`.
