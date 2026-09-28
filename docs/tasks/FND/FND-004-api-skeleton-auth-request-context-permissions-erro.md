# FND-004: API skeleton: auth, request context, permissions, errors

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | Backlog |
| Size | M |
| Depends on | [FND-003](../FND/FND-003-core-schema-identity-workspaces-members-department.md) |
| Requirements | NFR-01, NFR-02 |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/BACKEND.md`](../../architecture/BACKEND.md), [`architecture/MULTI_TENANCY.md §2`](../../architecture/MULTI_TENANCY.md), [`architecture/SECURITY.md §1–2`](../../architecture/SECURITY.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Every API request is authenticated, bound to a workspace and role, and errors follow one format — the base all endpoints build on.

## Scope
**In:**
- pydantic-settings config; async DB session
- Supabase JWT verification via JWKS (cached)
- `RequestContext` + `X-Workspace-Id` membership resolution; candidate and public contexts
- `permissions.can()` implementing the SECURITY.md matrix; `require()` dependency
- problem+json error handler with stable codes; request ID middleware; CORS from `WEB_ORIGINS`
- Repository base class that requires `workspace_id`; tenancy test harness (two workspaces, all roles)
- `GET /me`, `GET /me/workspaces`

**Out:**
- Business endpoints

## Acceptance criteria
- [ ] Invalid/expired JWT → 401; non-member workspace → 403 `not_a_member`
- [ ] Permission matrix unit-tested for every action/role
- [ ] Tenancy harness usable by later tasks with one decorator/fixture
- [ ] OpenAPI served at `/v1/openapi.json`
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Return 404 for resources outside scope (not 403)

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Unit: JWT verification, permissions
- Integration: /me endpoints

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
