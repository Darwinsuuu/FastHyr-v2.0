# INTV-001: Interview plan generation

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M3 Intake |
| Status | Backlog |
| Size | M |
| Depends on | [SCREEN-002](../SCREEN/SCREEN-002-resume-assessment-and-decision.md) |
| Requirements | FR-INTV-01 |
| Gap areas | G2, G3 |
| Design | Frames Demo/DemoInterview (topics, résumé quotes), CandidateProfile (topics) |
| Docs to read | [`architecture/AI_PIPELINE.md §2`](../../architecture/AI_PIPELINE.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Every invited candidate has a personal interview plan built from the JD, their redacted résumé and the pipeline's settings.

## Scope
**In:**
- `interview_plans` migration
- Prompt `interview_plan@v1` + schema
- `plan_interview` job
- Validation: every skill to probe covered; warm-up first; candidate questions last

**Out:**
- —

## Acceptance criteria
- [ ] Plans generated for golden fixtures
- [ ] No personal data in plan text
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- ai_eval plan fixtures

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
