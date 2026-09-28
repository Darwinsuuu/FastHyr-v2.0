# PIPE-003: New pipeline wizard — Scoring, Schedule & credits, Review, Publish

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M2 Pipelines |
| Status | Backlog |
| Size | L |
| Depends on | [PIPE-002](../PIPE/PIPE-002-new-pipeline-wizard-role-and-ai-interview-steps.md) |
| Requirements | FR-PIPE-03, FR-PIPE-04, FR-PIPE-05, FR-PIPE-06 |
| Gap areas | G4, G5 |
| Design | Frame NewPipeline steps 3–5, done state |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users set scoring, schedule and credits, review everything and publish with a clear lock warning.

## Scope
**In:**
- Rubric sliders with sum check, pass mark, message toggles
- Open now/scheduled, duration, close date, credit reserve stepper with free-credit check
- Review cards with Edit links
- Type-to-confirm publish/schedule dialog
- Done state with share tiles (PIPE-006 component)
- Edit setup for scheduled pipelines

**Out:**
- —

## Acceptance criteria
- [ ] Can't continue unless weights = 100
- [ ] Reserve > free credits shows the designed warning and blocks publish
- [ ] Publishing live locks setup; scheduled stays editable until open
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Playwright: create and publish a pipeline

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
