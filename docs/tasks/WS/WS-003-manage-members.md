# WS-003: Manage members

| Field | Value |
|---|---|
| Epic | WS — Workspace admin |
| Milestone | M1 Access |
| Status | Backlog |
| Size | M |
| Depends on | [WS-002](../WS/WS-002-departments.md) |
| Requirements | FR-WS-04, FR-WS-05 |
| Gap areas | — |
| Design | Frame ManageMembers |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Admins see and manage who has access and to which departments.

## Scope
**In:**
- Members tab with filters/search/pagination
- Edit access dialog (role + departments)
- Remove access dialog
- Role explainer card

**Out:**
- Invites (WS-004)

## Acceptance criteria
- [ ] Owner cannot be removed/demoted
- [ ] Changes take effect on next request
- [ ] last_active_at updated (throttled)
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
