# AUTH-003: Workspaces: create, join by code, select, switch

| Field | Value |
|---|---|
| Epic | AUTH — Authentication & workspaces |
| Milestone | M1 Access |
| Status | Backlog |
| Size | M |
| Depends on | [AUTH-001](../AUTH/AUTH-001-employer-sign-in.md), [FND-003](../FND/FND-003-core-schema-identity-workspaces-members-department.md), [BILL-002](../BILL/BILL-002-credit-ledger-service.md) |
| Requirements | FR-AUTH-04, FR-AUTH-05, FR-AUTH-06, FR-AUTH-07 |
| Gap areas | — |
| Design | Frame WorkspaceSelect, app shell switcher |
| Docs to read | [`architecture/MULTI_TENANCY.md`](../../architecture/MULTI_TENANCY.md), [`decisions/ADR-005-tenancy-and-roles.md`](../../decisions/ADR-005-tenancy-and-roles.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
A signed-in TA user can create a workspace (becoming owner with trial credits), join one with a code, and switch between workspaces.

## Scope
**In:**
- `/workspaces` page
- `POST /workspaces` (slug generation, owner membership, company profile stub, trial grant, default email templates hook)
- Join by code from this page (uses invite accept API)
- Active workspace cookie + `profiles.last_workspace_id`

**Out:**
- Invite link page (AUTH-004)

## Acceptance criteria
- [ ] Creating a workspace grants 20 trial credits and opens Getting started
- [ ] Switching clears cached data
- [ ] Slug unique and URL-safe
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Integration tests for create/join

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
