# ASMT-009: Candidate report PDF and résumé download

| Field | Value |
|---|---|
| Epic | ASMT — Assessment & review |
| Milestone | M5 Review |
| Status | Backlog |
| Size | M |
| Depends on | [ASMT-004](../ASMT/ASMT-004-candidate-profile-header-and-overview-tab.md), [PIPE-010](../PIPE/PIPE-010-pipelines-report-pdf.md) |
| Requirements | FR-ASMT-08 |
| Gap areas | — |
| Design | Frames PipelineView/CandidateProfile (download dialogs) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users download a branded candidate report and the original résumé.

## Scope
**In:**
- Candidate report template + job steps
- Résumé download job/dialog
- Audit 'data exported'

**Out:**
- —

## Acceptance criteria
- [ ] Report includes résumé analysis, highlights, rubric, summary, evidence
- [ ] HM allowed for shortlisted only
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
