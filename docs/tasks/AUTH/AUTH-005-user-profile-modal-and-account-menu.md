# AUTH-005: User profile modal and account menu

| Field | Value |
|---|---|
| Epic | AUTH — Authentication & workspaces |
| Milestone | M1 Access |
| Status | Backlog |
| Size | S |
| Depends on | [DASH-001](../DASH/DASH-001-app-shell.md) |
| Requirements | FR-AUTH-08, FR-AUTH-09 |
| Gap areas | — |
| Design | Frame WorkspaceSelect (modal) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Users can see their account details and log out from anywhere.

## Scope
**In:**
- Account menu and profile modal (email verified, sign-in method, last sign-in, created, user ID copy)

**Out:**
- —

## Acceptance criteria
- [ ] Modal matches design; copy button works; keyboard accessible
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
