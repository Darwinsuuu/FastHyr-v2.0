# ASMT-004: Candidate profile — header and Overview tab

| Field | Value |
|---|---|
| Epic | ASMT — Assessment & review |
| Milestone | M5 Review |
| Status | Backlog |
| Size | L |
| Depends on | [ASMT-001](../ASMT/ASMT-001-interview-scoring.md), [PIPE-008](../PIPE/PIPE-008-pipeline-details-candidates-tab.md) |
| Requirements | FR-ASMT-07 |
| Gap areas | G4 |
| Design | Frame CandidateProfile (Overview) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users see how a score was reached, the evidence behind it and how the candidate compares.

## Scope
**In:**
- `GET /applications/{id}` payload
- Header (stage, fit, applications link, email, report, advance/reject)
- Overall score, 'How we got to', why each score with evidence jump links, distribution, comparisons, topics radar, history, Ava summary refs, strengths, probes, résumé match, answer patterns, integrity card, journey, fairness note

**Out:**
- —

## Acceptance criteria
- [ ] Every evidence link seeks the recording
- [ ] HM view read-only
- [ ] No candidate PII in URL
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
