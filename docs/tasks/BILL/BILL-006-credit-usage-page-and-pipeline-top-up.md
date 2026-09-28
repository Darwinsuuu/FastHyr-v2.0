# BILL-006: Credit usage page and pipeline top-up

| Field | Value |
|---|---|
| Epic | BILL — Billing & credits |
| Milestone | M6 Billing & analytics |
| Status | Backlog |
| Size | M |
| Depends on | [BILL-002](../BILL/BILL-002-credit-ledger-service.md), [PIPE-004](../PIPE/PIPE-004-pipelines-list.md), [DASH-003](../DASH/DASH-003-analytics-views-and-endpoints.md) |
| Requirements | FR-BILL-04, FR-BILL-08 |
| Gap areas | G8 |
| Design | Frame CreditUsage |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Admins and recruiters see where credits go and top up pipelines before they pause.

## Scope
**In:**
- KPIs, split bar, monthly chart, by department, alerts
- Per-pipeline table with outlook and tabs
- Top-up modal (+25/50/100/200) with pace estimate
- Ledger table with grouping and pagination

**Out:**
- —

## Acceptance criteria
- [ ] Top-up of a paused-for-credits pipeline resumes it
- [ ] Recruiters top up only their departments
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
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
