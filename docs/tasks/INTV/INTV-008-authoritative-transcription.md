# INTV-008: Authoritative transcription

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M4 AI interview |
| Status | Backlog |
| Size | M |
| Depends on | [INTV-006](../INTV/INTV-006-recording-capture-and-finalisation.md) |
| Requirements | FR-ASMT-01 |
| Gap areas | — |
| Design | Frame CandidateProfile (transcript) |
| Docs to read | [`architecture/MEDIA.md §4`](../../architecture/MEDIA.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Each interview has an accurate, timestamped, speaker-separated transcript that scoring and review rely on.

## Scope
**In:**
- `transcript_segments` migration + full-text index
- `transcribe_interview` job (splitting, diarisation, speaker mapping, topic alignment)

**Out:**
- —

## Acceptance criteria
- [ ] Segments ordered with correct timestamps
- [ ] Speaker mapping correct on fixtures
- [ ] Third speaker preserved as `other`
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
