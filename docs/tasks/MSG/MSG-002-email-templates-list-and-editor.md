# MSG-002: Email templates list and editor

| Field | Value |
|---|---|
| Epic | MSG — Candidate emails |
| Milestone | M3 Intake |
| Status | Backlog |
| Size | M |
| Depends on | [MSG-001](../MSG/MSG-001-email-templates-model-and-defaults.md), [DASH-001](../DASH/DASH-001-app-shell.md) |
| Requirements | FR-MSG-02 |
| Gap areas | G5 |
| Design | Frames EmailTemplates, EditEmailTemplate + A-07 |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users adjust the wording of every candidate email, test it and restore earlier versions.

## Scope
**In:**
- List with filters and edited-by info
- Tiptap editor (bold, italic, link, bullets, parameter chips), subject
- Reset to default, version history view/restore, send test to me

**Out:**
- —

## Acceptance criteria
- [ ] Saved HTML sanitised
- [ ] Restore creates a new version
- [ ] Admins and Recruiters only
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
