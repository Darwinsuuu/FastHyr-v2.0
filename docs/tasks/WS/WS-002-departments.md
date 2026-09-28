# WS-002: Departments

| Field | Value |
|---|---|
| Epic | WS — Workspace admin |
| Milestone | M1 Access |
| Status | Backlog |
| Size | S |
| Depends on | [DASH-001](../DASH/DASH-001-app-shell.md) |
| Requirements | FR-WS-02 |
| Gap areas | — |
| Design | Frame Departments |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Admins group pipelines into departments that also scope member access.

## Scope
**In:**
- List with stats, search, pagination
- Add/edit/delete dialogs with rules (unique, reserved name, delete moves pipelines)
- API endpoints

**Out:**
- —

## Acceptance criteria
- [ ] Deleting a department moves its pipelines to No department and removes member access
- [ ] Counts correct
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Tenancy tests

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
