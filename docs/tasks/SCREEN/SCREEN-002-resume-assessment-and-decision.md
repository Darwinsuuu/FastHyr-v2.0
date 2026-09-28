# SCREEN-002: Résumé assessment and decision

| Field | Value |
|---|---|
| Epic | SCREEN — Résumé screening |
| Milestone | M3 Intake |
| Status | Backlog |
| Size | L |
| Depends on | [SCREEN-001](../SCREEN/SCREEN-001-resume-text-extraction-and-pii-redaction.md), [PIPE-001](../PIPE/PIPE-001-pipeline-model-and-state-machine.md) |
| Requirements | FR-SCREEN-03, FR-SCREEN-04, FR-SCREEN-05, FR-SCREEN-06 |
| Gap areas | G2, G4 |
| Design | Frame CandidateProfile (Résumé tab data) |
| Docs to read | [`architecture/AI_PIPELINE.md §1`](../../architecture/AI_PIPELINE.md), [`decisions/ADR-013-resume-screening-rule.md`](../../decisions/ADR-013-resume-screening-rule.md), [`decisions/ADR-015-automated-decisions-human-review.md`](../../decisions/ADR-015-automated-decisions-human-review.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Each résumé gets an explainable fit score against the pipeline's criteria and a pass/fail decision, logged for audit.

## Scope
**In:**
- `resume_assessments` + `ai_decisions` migrations
- Prompt `resume_assessment@v1` + schema
- Score computed in code (40/20/25/15, redistribution)
- 'Also open to' rules
- `screen_resume` job end-to-end

**Out:**
- Emails and invites (SCREEN-003)

## Acceptance criteria
- [ ] Pass rule = score ≥ bar and all must-haves met
- [ ] Counterfactual pairs within ±3 points
- [ ] p95 < 5 min on the QA environment
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- ai_eval golden set

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
