# FND-004: API skeleton: auth, request context, permissions, errors

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | In review |
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
- [x] Invalid/expired JWT → 401; non-member workspace → 403 `not_a_member`
- [x] Permission matrix unit-tested for every action/role
- [x] Tenancy harness usable by later tasks with one decorator/fixture
- [x] OpenAPI served at `/v1/openapi.json`
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Return 404 for resources outside scope (not 403)

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Unit: JWT verification, permissions
- Integration: /me endpoints

## Implementation plan
Branch: `feature/api-skeleton` from `develop`. Also sets FND-003 to Done on the board (merged in PR #4).

- **Config and DB:** `core/config.py` adds `SUPABASE_JWKS_URL`, `SUPABASE_JWT_ISSUER` (both derived from `SUPABASE_URL` when empty) and `SUPABASE_JWT_AUDIENCE`. `core/db.py`: async engine (asyncpg) created in the app lifespan, one session per request, rolled back if left uncommitted.
- **Auth (`core/auth.py`):** verify the Supabase access token against the JWKS (cached 10 min, refetched on an unknown key ID): signature, `exp`, `aud`, `iss`. Returns `CurrentUser(user_id, email, email_verified)`; anything wrong → `401 unauthenticated`.
- **Context (`core/context.py`, `api/deps.py`):** `RequestContext(user_id, workspace_id, member_id, role, is_owner, department_ids)` from `X-Workspace-Id` and an active `workspace_members` row; none → `403 not_a_member`. Admins see all departments and No department. `CandidateContext`, `PublicContext`, `SystemContext` for candidate routes, the apply page and jobs.
- **Permissions (`core/permissions.py`):** `Action` enum covering every SECURITY.md row; `can(ctx, action)` returns the access width (`workspace`, `departments`, `shortlist`) or None. `require(action)` dependency → `403 forbidden` when the role may not act; resources outside scope are 404s from repositories.
- **Errors and middleware:** `AppError` hierarchy with stable codes → problem+json (FastAPI validation errors and crashes too), no personal data in bodies; request ID middleware; CORS from `WEB_ORIGINS` allowing `X-Workspace-Id`.
- **Repositories:** `WorkspaceRepository` base requires `workspace_id`; `_scoped()` adds the filter, `_get_or_404()` hides other workspaces. `UserRepository` for the user's own profile and memberships.
- **Endpoints:** `GET /v1/me`, `GET /v1/me/workspaces`; OpenAPI at `/v1/openapi.json`; `/health` stays at the root.
- **Tests:** unit (JWT cases, full permission table, problem+json and request ID); tenancy harness fixture (two workspaces, every role, real sign-ins) with a cross-workspace 404 helper; integration tests for `/me`.
- **New dependency:** `pyjwt[crypto]`.

## Log
- 2026-09-28: plan approved by the owner; branch `feature/api-skeleton`; PR #5.
- Local Supabase (CLI 2.118.0) signs access tokens with ES256 and publishes the key at `/auth/v1/.well-known/jwks.json`, so local and hosted use the same JWKS path. The HS256 fallback considered in the plan was not needed: shared-secret tokens are refused everywhere.
- `email_verified` comes from the token's `user_metadata` (set by Supabase for email and OAuth sign-ups).
- Missing `X-Workspace-Id` is `400 workspace_required`; a malformed or unknown one is `403 not_a_member` (same as a workspace the user isn't in).
- `require()` refusals are `403 forbidden`: they only reveal what the caller's role can do in a workspace they already belong to. Rows outside workspace or department scope are `404 not_found` from repositories.
- Verified by hand against local Supabase: no token and a tampered token → 401 problem+json with `X-Request-Id`; `/v1/me` returns the signed-in user; `/v1/me/workspaces` lists only the user's active memberships with member counts; unknown route → 404 problem+json; `/v1/openapi.json` lists the endpoints; `make api-client` regenerates the TypeScript types.
- Tests: `tests/unit/test_auth.py`, `test_permissions.py` (hand-written table from SECURITY.md), `test_errors.py`; `tests/tenancy/harness.py` (the `tenancy` fixture) and `test_request_context.py`; `tests/integration/test_me.py`. The shared `supabase` fixture moved to `tests/conftest.py`.
- Additions beyond the plan: `app/schemas/` for Pydantic response models; `workspace_required` error code.
