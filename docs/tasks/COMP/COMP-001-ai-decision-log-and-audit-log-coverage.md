# COMP-001: AI decision log and audit log coverage

| Field | Value |
|---|---|
| Epic | COMP — Compliance |
| Milestone | M8 Launch readiness |
| Status | Ready |
| Size | M |
| Depends on | [SCREEN-002](../SCREEN/SCREEN-002-resume-assessment-and-decision.md), [ASMT-001](../ASMT/ASMT-001-interview-scoring.md), [ASMT-002](../ASMT/ASMT-002-integrity-checks-worker.md) |
| Requirements | FR-COMP-02, FR-COMP-04 |
| Gap areas | G2 |
| Design | — |
| Docs to read | [`architecture/SECURITY.md §5`](../../architecture/SECURITY.md), [`decisions/ADR-015-automated-decisions-human-review.md`](../../decisions/ADR-015-automated-decisions-human-review.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Every AI decision and sensitive action is recorded so any outcome can be explained later.

## Scope
**In:**
- Verify all decision points write `ai_decisions`
- Verify audit coverage for the SECURITY.md §5 list
- Append-only enforcement (DB permissions/trigger)
- Internal export script for a single application's decision trail

**Out:**
- —

## Acceptance criteria
- [ ] Tests assert log rows for each decision type and audited action
- [ ] Updates/deletes on append-only tables fail
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
