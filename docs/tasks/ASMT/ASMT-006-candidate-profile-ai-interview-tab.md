# ASMT-006: Candidate profile — AI interview tab

| Field | Value |
|---|---|
| Epic | ASMT — Assessment & review |
| Milestone | M5 Review |
| Status | Backlog |
| Size | M |
| Depends on | [ASMT-004](../ASMT/ASMT-004-candidate-profile-header-and-overview-tab.md), [INTV-008](../INTV/INTV-008-authoritative-transcription.md) |
| Requirements | FR-ASMT-07 |
| Gap areas | — |
| Design | Frame CandidateProfile (AI interview) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users watch or listen to the interview, jump to topics and search the transcript.

## Scope
**In:**
- Stats row
- Video/audio player with topic markers
- Topics list with scores
- Transcript with search and click-to-seek
- Interviewer labelled 'AI interviewer' (ADR-018)

**Out:**
- —

## Acceptance criteria
- [ ] Search highlights matches
- [ ] Player handles URL expiry
- [ ] Keyboard controls
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
