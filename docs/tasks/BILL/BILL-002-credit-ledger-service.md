# BILL-002: Credit ledger service

| Field | Value |
|---|---|
| Epic | BILL — Billing & credits |
| Milestone | M1 Access |
| Status | Done |
| Size | L |
| Depends on | [FND-003](../FND/FND-003-core-schema-identity-workspaces-members-department.md) |
| Requirements | FR-BILL-02, FR-BILL-03, FR-BILL-04 |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/BILLING.md §2–4`](../../architecture/BILLING.md), [`decisions/ADR-010-credit-used-on-apply.md`](../../decisions/ADR-010-credit-used-on-apply.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
One service owns every credit change: grants, reserves, consumption, releases and expiry, with an audit-proof ledger.

## Scope
**In:**
- `credit_batches`, `credit_ledger` migrations
- `services/credits.py` operations with row locks
- Trial grant
- Expiry cron
- Balance/free/reserved queries

**Out:**
- Stripe-triggered grants (wired in BILL-001/004/005)

## Acceptance criteria
- [x] Property tests: balance never negative; ledger sums equal balances
- [x] Consumption order plan → trial → extra by expiry
- [x] Concurrent consumes safe
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- AUTH-003 shipped before this task: `POST /workspaces` sets `workspaces.trial_granted_at` and calls the empty `grant_trial()` in `app/services/workspaces.py`. Fill it in through `services/credits.py`, and backfill a 20-credit trial batch (30 days from the workspace's `trial_granted_at`) for every workspace that has `trial_granted_at` and no trial batch.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Concurrency tests

## Implementation plan
Approved by the owner on 2026-09-29. Branch: `feature/credit-ledger-lisr7d` from `develop`.

**Dependencies not built yet, and what this task does instead**
- **Pipelines (PIPE-001):** this task creates `pipelines` with only what the ledger needs (`id`, `workspace_id`, `status` with the full WORKFLOW.md §2 check, `credits_reserved`, `credits_used`, `created_at`, `updated_at`, `unique (workspace_id, id)`), so reserve, consume and release are tested for real now. PIPE-001 adds the other columns.
- **Applications (APPLY-003):** `credit_ledger.application_id` is a plain uuid; APPLY-003 adds the FK.
- **Worker (FND-008):** expiry ships as `credits.expire_batches()`; FND-008 registers the hourly `expire_credit_batches` cron. Balance already ignores expired batches, so correctness doesn't wait on the cron.
- **Stripe (BILL-001/004/005):** `grant_plan`, `top_up_plan` and `grant_extra` are built and tested; only the webhook calls come later.

**Database (one migration):** `credit_batches` (checks, one trial per workspace, partial index), append-only `credit_ledger` (trigger + API role gets only `select, insert`), minimal `pipelines`; RLS on, no client policies; models mirror it. Backfill: every workspace with `trial_granted_at` and no trial batch gets 20 credits expiring 30 days after `trial_granted_at`, plus its `grant_trial` ledger row.

**`services/credits.py`:** each operation runs in the caller's transaction and first locks the **workspace row** (`FOR UPDATE`). BILLING.md said the workspace's batches; the workspace row is stricter and also covers a first grant with no batches, so BILLING.md is updated. Operations: `grant_trial` (idempotent), `grant_plan`, `top_up_plan`, `grant_extra`, `reserve` (`insufficient_free_credits`), `consume` (locks the pipeline, plan → trial → extra by earliest expiry, pauses the pipeline when its reserve runs out and every live pipeline when the balance hits 0, `pipeline_not_accepting` otherwise), `release`, `expire_batches`, `summary`.

**No endpoints:** BILL-003 and BILL-006 add them.

**Tests:** seeded random sequences (property test) checking non-negative balances, ledger sum = batches' remaining, `credits_used ≤ credits_reserved`; consumption order; 20 concurrent consumes against 5 reserved; two pipelines racing for the last credit; trial grant; append-only ledger.

## Log
- 2026-09-29: branch `feature/credit-ledger-lisr7d`; plan approved by the owner.
- **Workspace-row lock** instead of the batches (see plan); BILLING.md §3 updated.
- **`balance_after`** is the unexpired balance after the change, so a batch that has expired but isn't zeroed yet doesn't count. The ledger's `amount` always sums to the batches' `remaining`; the two only differ from Balance until the expiry job runs.
- **Out-of-credits side effects:** `consume` sets `paused_no_credits` on the pipeline and, at Balance 0, on every live pipeline; `expire_batches` does the same when expiry empties a workspace. The Overview alert and the owner email come with DASH-004 and MSG tasks. Resuming after a top-up belongs to PIPE-001's state machine.
- **Test cleanup:** the ledger rejects deletes even in tests, so `delete_credit_rows()` (tests/conftest.py) connects as the table owner (`SUPABASE_DB_URL`, default local `postgres`) with `session_replication_role = replica`.
- **Hand test:** migration applied on a database holding AUTH-003-era workspaces (a 2-day-old and a 40-day-old trial got their batches, a workspace without `trial_granted_at` didn't); then trial 20 + plan 5 + extra 3, reserve 29 → `insufficient_free_credits`, reserve 10, 25 concurrent consumes → 10 used (plan 5 then trial 5), 15 refused, pipeline `paused_no_credits`; expiry at day 31 zeroed the plan and trial batches; ledger sum = batches' remaining.
