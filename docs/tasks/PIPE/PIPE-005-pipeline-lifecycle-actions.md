# PIPE-005: Pipeline lifecycle actions

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M2 Pipelines |
| Status | Backlog |
| Size | M |
| Depends on | [PIPE-004](../PIPE/PIPE-004-pipelines-list.md), [FND-010](../FND/FND-010-email-infrastructure-resend.md) |
| Requirements | FR-PIPE-07 |
| Gap areas | G5 |
| Design | Frame PipelinesV2 (modals) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users pause, resume, close, cancel, archive, start now and duplicate pipelines from the list and detail header.

## Scope
**In:**
- Pause, close (with Role closed email option), cancel, archive dialogs as designed
- Resume, start now, duplicate as new draft
- Top-up entry point → BILL-006 modal

**Out:**
- —

## Acceptance criteria
- [ ] Each action matches its dialog copy and resulting state
- [ ] Close with notify queues `role_closed` emails to candidates without a final outcome
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Until MSG-001 lands, the role-closed email uses the default template file shipped with the API

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
