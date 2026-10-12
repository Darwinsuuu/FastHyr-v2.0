# PIPE-009: Pipeline details — Setup tab and duplicate

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M5 Review |
| Status | Ready |
| Size | S |
| Depends on | [PIPE-007](../PIPE/PIPE-007-pipeline-details-header-and-dashboard-tab.md) |
| Requirements | FR-PIPE-14 |
| Gap areas | — |
| Design | Frame PipelineView (Setup) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users see exactly how a locked pipeline was set up and can start a new one from it.

## Scope
**In:**
- Read-only setup cards incl. nice-to-haves and résumé pass bar
- Duplicate as new pipeline → wizard with copied draft

**Out:**
- —

## Acceptance criteria
- [ ] All setup fields shown
- [ ] Duplicate gets a new slug and draft status
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
