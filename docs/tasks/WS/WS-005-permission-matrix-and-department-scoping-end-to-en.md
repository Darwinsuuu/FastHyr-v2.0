# WS-005: Permission matrix and department scoping end to end

| Field | Value |
|---|---|
| Epic | WS — Workspace admin |
| Milestone | M1 Access |
| Status | Backlog |
| Size | M |
| Depends on | [WS-003](../WS/WS-003-manage-members.md) |
| Requirements | FR-WS-06, FR-DASH-05, NFR-01 |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/SECURITY.md §2`](../../architecture/SECURITY.md), [`architecture/MULTI_TENANCY.md`](../../architecture/MULTI_TENANCY.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Role and department rules are enforced in every repository and mirrored in the UI, with tests proving it.

## Scope
**In:**
- Department filtering in repositories
- HM shortlist-only filter
- `lib/permissions.ts` UI gating + nav visibility
- CI check: every router endpoint listed in tenancy tests

**Out:**
- —

## Acceptance criteria
- [ ] Recruiter in Engineering cannot see Sales or No-department pipelines
- [ ] HM sees only shortlisted candidates
- [ ] CI fails for untested endpoints
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
