# PIPE-008: Pipeline details — Candidates tab

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M5 Review |
| Status | Ready |
| Size | M |
| Depends on | [PIPE-007](../PIPE/PIPE-007-pipeline-details-header-and-dashboard-tab.md), [APPLY-003](../APPLY/APPLY-003-application-submission-and-credit-use.md) |
| Requirements | FR-PIPE-12, FR-PIPE-13 |
| Gap areas | G5, G6, G7 |
| Design | Frame PipelineView (Candidates) + A-02, A-03 |
| Docs to read | [`design/SCREEN_SPECS.md A-02, A-03`](../../design/SCREEN_SPECS.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users filter a pipeline's candidates by stage and act on each one.

## Scope
**In:**
- Stage filters incl. Review requested, Advanced, Rejected
- Table with fit tooltip, source, applied time
- Row menu: profile, résumé, report, review flag, email, advance, reject (dialogs from ASMT-007)
- Polling while candidates are processing

**Out:**
- —

## Acceptance criteria
- [ ] Filter counts correct
- [ ] HM sees only shortlisted rows and no actions
- [ ] Search by name/email
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
