# INTV-010: Public demo

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M7 Public site & demo |
| Status | Backlog |
| Size | L |
| Depends on | [INTV-005](../INTV/INTV-005-live-interview-ui-client.md), [SCREEN-001](../SCREEN/SCREEN-001-resume-text-extraction-and-pii-redaction.md) |
| Requirements | FR-DEMO-01, FR-DEMO-02, FR-DEMO-03, FR-DEMO-04 |
| Gap areas | — |
| Design | Frames Demo, DemoDeviceCheck, DemoInterview + A-09 |
| Docs to read | [`design/SCREEN_SPECS.md A-09`](../../design/SCREEN_SPECS.md), [`architecture/SECURITY.md §4`](../../architecture/SECURITY.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Visitors try a real, short AI interview with their own résumé, with nothing kept afterwards.

## Scope
**In:**
- Demo setup (3 steps, templates, sample résumé)
- Demo session endpoints, 10-min cap, no recording
- Rate limits, bot protection, daily spend cap
- Hard delete within 24 h

**Out:**
- —

## Acceptance criteria
- [ ] Spend cap stops new demos with a friendly message
- [ ] Demo data never linked to a workspace
- [ ] Settings match the wizard (A-09)
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
