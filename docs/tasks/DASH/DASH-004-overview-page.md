# DASH-004: Overview page

| Field | Value |
|---|---|
| Epic | DASH — Dashboard |
| Milestone | M6 Billing & analytics |
| Status | Backlog |
| Size | M |
| Depends on | [DASH-003](../DASH/DASH-003-analytics-views-and-endpoints.md), [BILL-006](../BILL/BILL-006-credit-usage-page-and-pipeline-top-up.md), [ASMT-008](../ASMT/ASMT-008-human-review-requests.md) |
| Requirements | FR-DASH-02, FR-DASH-03, FR-DASH-04 |
| Gap areas | G1, G7, G8 |
| Design | Frame Overview + A-03 |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users start the day with KPIs and a list of what needs them.

## Scope
**In:**
- All Overview cards incl. Needs your attention (with review requests)
- Week/30 days toggle
- Links into filtered views

**Out:**
- —

## Acceptance criteria
- [ ] Every attention item links to the right filtered page
- [ ] Empty states for new workspaces
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
