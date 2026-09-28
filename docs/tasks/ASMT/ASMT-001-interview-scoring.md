# ASMT-001: Interview scoring

| Field | Value |
|---|---|
| Epic | ASMT — Assessment & review |
| Milestone | M5 Review |
| Status | Backlog |
| Size | L |
| Depends on | [INTV-008](../INTV/INTV-008-authoritative-transcription.md), [FND-013](../FND/FND-013-openai-integration-layer.md) |
| Requirements | FR-ASMT-02, FR-ASMT-03, FR-ASMT-04, FR-ASMT-05, FR-ASMT-09 |
| Gap areas | G2, G4 |
| Design | Frame CandidateProfile (overview data) |
| Docs to read | [`architecture/AI_PIPELINE.md §4`](../../architecture/AI_PIPELINE.md), [`decisions/ADR-011-numeric-explainable-scores.md`](../../decisions/ADR-011-numeric-explainable-scores.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Each finished interview gets an explainable assessment and the candidate moves to Ready for review or Didn't pass.

## Scope
**In:**
- `assessments` migration
- Prompt `interview_assessment@v1` + schema requiring evidence
- Overall/fit/answer stats computed in code; rubric snapshot
- `score_interview` job, stage update, `ai_decisions`
- Schedule `reject_interview` (3 business days) if enabled

**Out:**
- —

## Acceptance criteria
- [ ] Scores without evidence rejected
- [ ] Transcript counterfactuals within ±5 on communication
- [ ] p95 < 20 min
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- ai_eval scoring set

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
