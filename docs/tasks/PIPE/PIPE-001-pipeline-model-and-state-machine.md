# PIPE-001: Pipeline model and state machine

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M2 Pipelines |
| Status | Done |
| Size | M |
| Depends on | [FND-003](../FND/FND-003-core-schema-identity-workspaces-members-department.md), [FND-008](../FND/FND-008-background-worker-and-job-framework.md), [BILL-002](../BILL/BILL-002-credit-ledger-service.md) |
| Requirements | FR-PIPE-07, FR-PIPE-15 |
| Gap areas | G3, G4 |
| Design | — |
| Docs to read | [`product/WORKFLOW.md §2`](../../product/WORKFLOW.md), [`architecture/DATABASE.md (pipelines)`](../../architecture/DATABASE.md), [`architecture/BILLING.md §3`](../../architecture/BILLING.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Pipelines exist in the database with their full setup, a strict state machine, locking and scheduled open/close.

## Scope
**In:**
- `pipelines` migration incl. lock trigger
- `services/pipelines.py`: create draft, update draft, publish (reserve credits), start now, pause, resume, close (release), cancel (release), archive, duplicate
- Cron: open scheduled, close due
- Slug generation (unique per workspace, fixed after publish)
- Audit entries

**Out:**
- UI (PIPE-002..)

## Acceptance criteria
- [x] Every transition in WORKFLOW.md §2 covered by tests; invalid ones raise `invalid_transition`
- [x] Locked setup cannot change (DB trigger + service check)
- [x] Closing releases unused reserve via credits service
- [x] Scheduled pipeline opens within 1 min of `opens_at`
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Pausing never extends closes_at
- BILL-002 already created `pipelines` with `id`, `workspace_id`, `status` (full check), `credits_reserved`, `credits_used`, `created_at`, `updated_at` and `unique (workspace_id, id)`. Add the other columns with `alter table` (existing rows are test-only), and use `services/credits.reserve`/`release` for publish, top-up, close and cancel. `consume` already moves a pipeline to `paused_no_credits`; resuming after a top-up is this task's state machine.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- State-machine table-driven tests

## Implementation plan
_(Auto-approved: the product owner asked for no plan approvals, 2026-09-29.)_

**Migration** `supabase/migrations/20261002090000_pipeline_setup.sql`
- `alter table pipelines` adds every DATABASE.md column. Setup columns are nullable because a draft can be saved at any wizard step; publishing checks they are complete. Defaults from the requirements: `resume_pass_bar` 60, `link_expiry_days` 5, `reminder_enabled` and `integrity_enabled` on, `pass_mark` 70, both candidate email toggles on.
- One extra column, `credits_to_reserve` (the reserve chosen in the wizard, so a draft keeps it; publish reserves it, min 10, step 10). `owner_id` and `published_by` are workspace member IDs (composite FKs to `workspace_members`).
- Checks for every enum, ranges, weights summing to 100, `must_haves`/`skills_to_probe` sizes, `closed_reason` only on closed pipelines, `archived_at` only on closed/cancelled ones, `slug` set once published.
- `pipelines_lock_setup` trigger: once `locked_at` is set, Role, AI interview, Scoring and Schedule columns can't change (`department_id` may still become null, which department deletion needs), and `slug` never changes after `published_at`.
- Indexes `(workspace_id, status)`, unique `(workspace_id, slug)`, plus partial indexes for the cron (`opens_at` of scheduled, `closes_at` of open pipelines).

**API**
- `app/models/pipelines.py`: the new columns. `app/repositories/pipelines.py`: workspace- and department-scoped (non-Admins only reach pipelines in their departments, else 404); `lock()` takes the workspace row then the pipeline row `FOR UPDATE`, the same order as the credit service.
- `app/services/pipelines.py`: `create_draft`, `update` (draft or scheduled only; otherwise `409 pipeline_locked`), `publish` (`422 pipeline_incomplete` with the missing fields; reserves through `credits.reserve`; slug from the title, unique per workspace), `start_now`, `pause`, `resume`, `close` (releases the unused reserve), `cancel` (scheduled only, releases), `archive`, `duplicate` (new draft with `duplicated_from_id`), `top_up` (reserves more; a `paused_no_credits` pipeline goes back to live), `open_due` / `close_due` for the cron. One transition table drives them; anything else is `409 invalid_transition`. Going live when the pipeline has no reserve left or the workspace no credits lands in `paused_no_credits`, matching BILLING.md §3. Every action writes an audit row.
- `app/core/slugs.py`: `slugify()` (ASCII, lowercase, hyphens, 60 chars) and the `-2`, `-3` suffix rule.
- Cron `open_and_close_pipelines` every minute in `app/jobs/system.py`, registered in `app/worker.py`.
- Routes under `/v1/pipelines` per API.md: `POST`, `GET/PATCH /{id}`, `/publish`, `/start-now`, `/pause`, `/resume`, `/close`, `/cancel`, `/archive`, `/duplicate`, `/top-up`. The list (PIPE-004) and share links (PIPE-006) stay with their tasks. Regenerate `packages/api-client`.
- `AppError` gains optional `errors` so `pipeline_incomplete` lists the fields.

**Seed:** Acme Talent pipelines get titles, setup, slugs and dates that match their status.

**Tests:** table-driven state machine (every allowed transition and every other one raising `invalid_transition`), the lock trigger at the database, closing/cancelling releases the reserve, the cron opens a due pipeline and closes an expired one, slugs are unique and fixed, department scoping and cross-workspace 404, plus unit tests for `slugify`.

**Docs:** DATABASE.md, API.md, BACKEND.md crons, AGENTS.md status, BOARD.md (PIPE-001 In review; FND-007 Done #26; M0 count; missing PR numbers).

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
- 2026-10-02: branch `feature/pipeline-model`. Plan auto-approved (owner's rule, 2026-09-29).
- Decisions: setup columns nullable so drafts save at any step, checked on publish (`422 pipeline_incomplete` with `errors`). Added `credits_to_reserve` so a draft keeps the wizard's reserve (DATABASE.md updated). `owner_id`/`published_by` are member IDs. Slug is set on publish, not on draft. Weights must total 100 whenever all three are set, even on a draft (the DB check). Email toggles default on. Start now runs the full duration from now (`closes_at` = now + duration). Going live with no reserve or workspace credits lands in `paused_no_credits`. One every-minute cron `open_and_close_pipelines` replaces the two crons BACKEND.md listed. The `/v1/pipelines` routes for create, edit and lifecycle are in this task so PIPE-002..005 build only UI; the list and share links stay with PIPE-004 and PIPE-006. `resume_after_credits_added()` is ready for BILL-001/005 to call after granting credits.
- Lock trigger lets `department_id` become null on a locked pipeline, because deleting a department moves its pipelines to No department (WS-002).
- Board housekeeping: FND-007 Done (#26), M0 count 14, PR numbers for AUTH-005 (#18) and WS-004 (#17), and SCREEN-001, COMP-002, WEB-001, WEB-002, WEB-003, WEB-005 to Ready (their dependencies are Done).
- Tested by hand against local Supabase with the Acme Talent seed: every action through the API, department scoping for Maria (Recruiter) and Jomar (Hiring manager), the lock trigger in SQL, and the real worker opening a due scheduled pipeline and closing an expired one within a minute.
