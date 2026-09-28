# ASMT-003: Flag review UI

| Field | Value |
|---|---|
| Epic | ASMT — Assessment & review |
| Milestone | M5 Review |
| Status | Backlog |
| Size | S |
| Depends on | [ASMT-002](../ASMT/ASMT-002-integrity-checks-worker.md), [ASMT-004](../ASMT/ASMT-004-candidate-profile-header-and-overview-tab.md) |
| Requirements | FR-ASMT-06 |
| Gap areas | G7 |
| Design | Frame CandidateProfile (integrity) + A-04 |
| Docs to read | [`design/SCREEN_SPECS.md A-04`](../../design/SCREEN_SPECS.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users review each flag with context and record their conclusion.

## Scope
**In:**
- Flag panel with jump-to moments and guidance
- Resolve (No concern / Concern confirmed + note)
- Flagged overlay cleared when all resolved

**Out:**
- —

## Acceptance criteria
- [ ] Resolution audited
- [ ] Advance enabled only after all flags resolved
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
