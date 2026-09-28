# COMP-004: Bias evaluation suite

| Field | Value |
|---|---|
| Epic | COMP — Compliance |
| Milestone | M8 Launch readiness |
| Status | Backlog |
| Size | M |
| Depends on | [SCREEN-002](../SCREEN/SCREEN-002-resume-assessment-and-decision.md), [ASMT-001](../ASMT/ASMT-001-interview-scoring.md), [AVA-001](../AVA/AVA-001-ava-backend-scoped-assistant.md) |
| Requirements | FR-COMP-06 |
| Gap areas | G2 |
| Design | — |
| Docs to read | [`compliance/BIAS_FAIRNESS.md §3–4`](../../compliance/BIAS_FAIRNESS.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Prompt and model changes are checked for bias before release, and production fairness is monitored.

## Scope
**In:**
- Counterfactual résumé and transcript sets
- CI workflow (manual/pre-release) with thresholds
- Monthly fairness report script (pass rates by source/'also open to')

**Out:**
- —

## Acceptance criteria
- [ ] Suite fails when counterfactual deltas exceed thresholds
- [ ] Report runs against the QA environment
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
