# PIPE-010: Pipelines report PDF

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M5 Review |
| Status | Backlog |
| Size | M |
| Depends on | [DASH-003](../DASH/DASH-003-analytics-views-and-endpoints.md), [FND-008](../FND/FND-008-background-worker-and-job-framework.md) |
| Requirements | FR-PIPE-09 |
| Gap areas | G8 |
| Design | Frame PipelinesV2 (Reports) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA leads download a PDF summarising pipelines for the selected range.

## Scope
**In:**
- `generate_report` job (pipelines report) with steps
- WeasyPrint template in brand style
- JobProgressDialog wiring

**Out:**
- —

## Acceptance criteria
- [ ] Progress steps as designed; cancel works
- [ ] PDF contains summaries, funnel, sources, drop-offs, credit usage
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
