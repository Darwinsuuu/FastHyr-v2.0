# APPLY-003: Application submission and credit use

| Field | Value |
|---|---|
| Epic | APPLY — Apply |
| Milestone | M3 Intake |
| Status | In review |
| Size | L |
| Depends on | [APPLY-002](../APPLY/APPLY-002-candidate-sign-in-on-the-apply-page.md), [FND-011](../FND/FND-011-storage-service-and-pdf-handling.md), [BILL-002](../BILL/BILL-002-credit-ledger-service.md), [COMP-002](../COMP/COMP-002-notices-and-consent-versioning.md) |
| Requirements | FR-APPLY-03, FR-APPLY-04, FR-APPLY-05 |
| Gap areas | G2 |
| Design | Frame Apply (form, sent modal) |
| Docs to read | [`architecture/BILLING.md §3–4`](../../architecture/BILLING.md), [`product/WORKFLOW.md §3`](../../product/WORKFLOW.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Candidates submit a résumé and details; FastHyr records consent, uses one credit and starts screening.

## Scope
**In:**
- Form with validation and PDF upload via signed URL
- `POST /candidate/applications` (idempotent): pipeline live check, consume credit, upsert candidate, create application, store consent version, enqueue screening
- Sent modal and 'Applied on' state
- Pipeline auto-pauses when reserve runs out

**Out:**
- —

## Acceptance criteria
- [x] One application per candidate per pipeline
- [x] Race at last credit: only one succeeds, no credit used by the loser
- [x] Credit ledger entry links to the application
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Use 1 credit with `services/credits.consume(session, workspace_id, pipeline_id, application_id=…)` in the same transaction as the application insert (BILL-002). It raises `pipeline_not_accepting` without using a credit.
- Add the foreign key `credit_ledger (workspace_id, application_id) → applications (workspace_id, id)`; BILL-002 left `application_id` as a plain uuid because `applications` didn't exist yet.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Concurrency test for last-credit race

## Implementation plan
_(Auto-approved per the owner's standing rule: plans are written here and built without a separate approval.)_

**Database** (`supabase/migrations/20261002120000_applications.sql`, models in `app/models/applications.py`)
- `candidates` and `applications` as DATABASE.md describes (unique `(workspace_id, auth_user_id)` and `(pipeline_id, candidate_id)`, composite FKs to `pipelines` and `candidates`, stage/source/resume_status checks, the §indexes). RLS on with no policies, no grants for `anon`/`authenticated`.
- `credit_ledger (workspace_id, application_id) → applications (workspace_id, id)`, **deferrable initially deferred**: the credit is consumed first (so the workspace and pipeline rows are locked before anything else, in the same order as every credit change) and the application row follows in the same transaction. `applications.credit_ledger_id → credit_ledger (id)`.

**API** (`/v1/candidate/*`, signed-in candidate, `CandidateContext`)
- Candidate routes accept only Google or Microsoft sessions (ADR-014): `CurrentUser.provider` comes from the token's `app_metadata`; anything else is `403 candidate_sign_in_required`.
- `POST /candidate/pipelines/{pipeline_id}/resume-upload` → signed upload URL to `resumes/tmp/{workspace_id}/{upload_id}` (`files.create_upload`), only while the pipeline is live (`409 pipeline_not_accepting`); unpublished or unknown pipelines are 404.
- `POST /candidate/applications` (`services/applications.submit()`):
  1. pipeline live check; consent through `consents.accept("apply", …)` (`409 notice_outdated`, `422 notice_unknown`);
  2. an existing application for this candidate and pipeline is returned as is (`200`, `created: false`, no credit): this is what makes the call idempotent (FR-APPLY-05), so no separate idempotency-key table;
  3. `files.promote_pdf()` checks and sanitises the résumé into `resumes/{workspace_id}/{application_id}/resume.pdf` **before** any credit moves, so a bad file never uses a credit and the form can say what's wrong at once (STORAGE.md said the worker did this; updated);
  4. one transaction: `credits.consume(…, application_id=…)` (locks, may pause the pipeline), upsert the candidate (latest details win), insert the application (`processing_resume`, `resume_status = pending`, source, consent version/time, `consent_ip_hash` = HMAC-SHA256 of the client IP keyed from the service key, never the IP itself), set `credit_ledger_id`;
  5. a lost race (`pipeline_not_accepting`, or the unique key on a double submit) rolls back and deletes the stored résumé, so no credit is used by the loser;
  6. after commit, enqueue `screen_resume(application_id)` (new job; SCREEN-001/002 fill in the body).
- `GET /candidate/pipelines/{pipeline_id}/my-application` → `{applied_at}` (null when not applied) for the "Applied on" state. Candidates never see stage, scores or flags.

**Web** (`components/apply`)
- `ApplicationDialog` becomes the form from frame Apply: account row, résumé (kit `FileDrop`, which gains an `error` prop), full name (prefilled), email (read-only, "Verified by Google/Microsoft"), contact number (`PhoneInput`), current city, LinkedIn or portfolio, `ConsentCheckbox` with the apply notice loaded on the server. Validation as the frame; on Send: upload URL → PUT the file → submit with the stored `?source=` tag (`applySource()`).
- Sent modal ("Application sent", what happens next, Done); the page then shows "Applied on {date}" instead of Apply now, "We'll email {email} with next steps", and the "Your application is in" notice. The page reads `my-application` on the server for signed-in candidates so a reload keeps that state.
- API error codes map to messages (bad PDF under the résumé, role stopped accepting, notice changed, generic retry). APPLY-004 polishes the edge states.

**Tests** (after it works): concurrency test for the last credit (two applicants, one credit: one succeeds, the other gets 409 and no credit or file is left); one application per candidate per pipeline (second submit returns the first, no second credit); ledger entry links to the application; candidate-only routes refuse password sessions; web unit tests for the form rules.

**Docs**: API.md, DATABASE.md, STORAGE.md, BACKEND/AGENTS current status, BOARD (APPLY-003 In review, COMP-002 Done, APPLY-004 Ready).

## Log
- 2026-10-02: branch `feature/application-form-e2l7d0` from `develop`. Plan auto-approved (owner's standing rule).
- Decisions: the résumé is checked and stored inside the submit request (not the worker, as STORAGE.md had it) so a bad file never uses a credit; idempotency comes from the one-application-per-pipeline key, so no idempotency-key table; `credit_ledger.application_id`'s FK is deferred so the credit service's lock order stays the same; candidate routes refuse non-Google/Microsoft sessions (`candidate_sign_in_required`).
- Not in this task: `screen_resume` is queued but does nothing until SCREEN-001, which should also add stuck `pending` applications to `requeue_stuck_work`; the Acme Talent seed gets sample applications with the candidate list (PIPE-008); the "paused for credits" Overview alert and owner email come with DASH-004 and the notification tasks.
- Hand-tested on local Supabase with Google-style candidate accounts: apply with `?source=linkedin` (recorded), sent modal, "Applied on" after reload, missing fields, a non-PDF (422, no credit used), light and dark at 360/768/1024/1440. Screenshots in the project files under `screenshots/APPLY-003/`.
