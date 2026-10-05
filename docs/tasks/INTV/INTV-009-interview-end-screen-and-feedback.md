# INTV-009: Interview end screen and feedback

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M4 AI interview |
| Status | Ready |
| Size | S |
| Depends on | [INTV-006](../INTV/INTV-006-recording-capture-and-finalisation.md) |
| Requirements | FR-INTV-07 |
| Gap areas | G5 |
| Design | Frame DemoInterview (done) + S-02 |
| Docs to read | [`design/SCREEN_SPECS.md S-02`](../../design/SCREEN_SPECS.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Candidates finish knowing what happens next and can rate the experience privately.

## Scope
**In:**
- End screen with upload progress
- Rating + comment endpoint
- `interview_received` email trigger (if enabled)

**Out:**
- —

## Acceptance criteria
- [ ] Feedback never visible to employer
- [ ] Page doesn't say done until uploads finish
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
