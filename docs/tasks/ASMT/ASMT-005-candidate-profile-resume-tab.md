# ASMT-005: Candidate profile — Résumé tab

| Field | Value |
|---|---|
| Epic | ASMT — Assessment & review |
| Milestone | M5 Review |
| Status | Ready |
| Size | M |
| Depends on | [ASMT-004](../ASMT/ASMT-004-candidate-profile-header-and-overview-tab.md), [SCREEN-002](../SCREEN/SCREEN-002-resume-assessment-and-decision.md) |
| Requirements | FR-ASMT-07 |
| Gap areas | G2 |
| Design | Frame CandidateProfile (Résumé) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users see how the résumé was scored with the original PDF and highlighted evidence.

## Scope
**In:**
- Résumé fit summary + calculation
- PDF.js viewer with highlight layers (must-have, nice-to-have, impact)
- Must-have evidence, nice-to-haves, impact, claims checked, timeline, comparison, hidden-fields note
- Download original

**Out:**
- —

## Acceptance criteria
- [ ] Highlights align with quotes
- [ ] Signed URL refresh on expiry
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
