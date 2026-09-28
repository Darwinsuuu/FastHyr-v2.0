# DASH-001: App shell

| Field | Value |
|---|---|
| Epic | DASH — Dashboard |
| Milestone | M1 Access |
| Status | Backlog |
| Size | M |
| Depends on | [FND-012](../FND/FND-012-ui-kit-design-system-components.md), [AUTH-003](../AUTH/AUTH-003-workspaces-create-join-by-code-select-switch.md) |
| Requirements | FR-AUTH-07 |
| Gap areas | — |
| Design | All app frames (sidebar) |
| Docs to read | [`architecture/FRONTEND.md`](../../architecture/FRONTEND.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
The TA app has its persistent layout: sidebar, workspace switcher, role-aware navigation and user menu.

## Scope
**In:**
- Sidebar sections as designed
- Workspace switcher popover (role, member count, create/join)
- Nav items hidden by role
- Mobile first: top bar + slide-out drawer below `lg`, persistent sidebar from `lg`; switcher as bottom sheet on phones

**Out:**
- —

## Acceptance criteria
- [ ] Matches frames
- [ ] Hidden items also blocked by API
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
