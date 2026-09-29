# BILL-002: Credit ledger service

| Field | Value |
|---|---|
| Epic | BILL — Billing & credits |
| Milestone | M1 Access |
| Status | Backlog |
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
- [ ] Property tests: balance never negative; ledger sums equal balances
- [ ] Consumption order plan → trial → extra by expiry
- [ ] Concurrent consumes safe
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- AUTH-003 shipped before this task: `POST /workspaces` sets `workspaces.trial_granted_at` and calls the empty `grant_trial()` in `app/services/workspaces.py`. Fill it in through `services/credits.py`, and backfill a 20-credit trial batch (30 days from the workspace's `trial_granted_at`) for every workspace that has `trial_granted_at` and no trial batch.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Concurrency tests

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
