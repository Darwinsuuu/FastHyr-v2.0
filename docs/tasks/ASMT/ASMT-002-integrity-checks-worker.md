# ASMT-002: Integrity checks (worker)

| Field | Value |
|---|---|
| Epic | ASMT — Assessment & review |
| Milestone | M5 Review |
| Status | Backlog |
| Size | L |
| Depends on | [INTV-008](../INTV/INTV-008-authoritative-transcription.md) |
| Requirements | FR-ASMT-06 |
| Gap areas | G7 |
| Design | — |
| Docs to read | [`decisions/ADR-016-integrity-checks-scope.md`](../../decisions/ADR-016-integrity-checks-scope.md), [`architecture/MEDIA.md §5`](../../architecture/MEDIA.md), [`compliance/FRAUD_INTEGRITY.md`](../../compliance/FRAUD_INTEGRITY.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Possible impersonation is flagged at exact moments for human review — never as an automatic rejection.

## Scope
**In:**
- `integrity_flags` migration
- Frame sampling + local face embeddings (same face, no face)
- Second voice from diarisation
- Read-aloud/timing features + model judgement
- Respect biometric consent and pipeline toggle

**Out:**
- —

## Acceptance criteria
- [ ] No embeddings persisted
- [ ] Flags carry times and confidence
- [ ] Pipeline toggle off → no checks
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Fixtures with synthetic media

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
