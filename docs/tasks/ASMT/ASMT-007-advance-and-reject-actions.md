# ASMT-007: Advance and reject actions

| Field | Value |
|---|---|
| Epic | ASMT — Assessment & review |
| Milestone | M5 Review |
| Status | Backlog |
| Size | M |
| Depends on | [PIPE-008](../PIPE/PIPE-008-pipeline-details-candidates-tab.md), [MSG-003](../MSG/MSG-003-email-scheduling-and-sending-engine.md) |
| Requirements | FR-PIPE-13 |
| Gap areas | G5, G6 |
| Design | Frame PipelineView (reject dialog) + A-02 |
| Docs to read | [`decisions/ADR-017-manual-advance-action.md`](../../decisions/ADR-017-manual-advance-action.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users move candidates forward or reject them with a reason, and candidates are told.

## Scope
**In:**
- Reject dialog (reason required, email option)
- Advance dialog (note, email option)
- Endpoints with permission + stage rules
- Emails: next_stage / reject_* chosen by stage

**Out:**
- —

## Acceptance criteria
- [ ] Rejected/advanced are terminal
- [ ] Scheduled automatic emails cancelled when a TA acts
- [ ] HM cannot act
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Advance needs every integrity flag reviewed (A-02, FR-PIPE-13): refuse it while `applications.has_open_flags` is true; ASMT-003 clears the overlay when the last flag is reviewed (`PATCH /v1/integrity-flags/{id}`). The web already hides or disables Advance while `flagged`.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
