# REL-001: End-to-end test suite

| Field | Value |
|---|---|
| Epic | REL — Release |
| Milestone | M8 Launch readiness |
| Status | Backlog |
| Size | M |
| Depends on | [ASMT-007](../ASMT/ASMT-007-advance-and-reject-actions.md), [BILL-005](../BILL/BILL-005-buy-extra-credits.md) |
| Requirements | NFR-05 |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/DEPLOYMENT.md §3`](../../architecture/DEPLOYMENT.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Core journeys are protected by automated end-to-end tests.

## Scope
**In:**
- Playwright: sign up → workspace → pipeline publish; apply → screen → interview (fake media + fake Realtime) → score → advance; billing purchase in Stripe test mode; tenancy smoke

**Out:**
- —

## Acceptance criteria
- [ ] Suite green nightly on the QA environment
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
