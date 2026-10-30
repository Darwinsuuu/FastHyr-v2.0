# WS-005: Permission matrix and department scoping end to end

| Field | Value |
|---|---|
| Epic | WS — Workspace admin |
| Milestone | M1 Access |
| Status | Done |
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
- [x] Recruiter in Engineering cannot see Sales or No-department pipelines
- [x] HM sees only shortlisted candidates
- [x] CI fails for untested endpoints
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Auto-approved: Darwin's standing rule, no plan approvals.)_

The rules themselves already live in the code: `require(action)` on every TA route, and the
pipeline, application, analytics, review-request and flag repositories take the caller's
departments and the Hiring-manager shortlist (PIPE-001 onwards). What's missing is proof that
covers **every** endpoint and a check that keeps it that way. So this task is mostly tests, and
fixes for any gap they find.

1. **Endpoint registry** (`apps/api/tests/tenancy/endpoints.py`, no database): every route in
   `create_app()` falls in exactly one group:
   - `CASES`: workspace endpoints that read or change a workspace resource or list, each with the
     path parameters it needs, a valid body, and whether it is department scoped and/or
     shortlist scoped;
   - `CALLER_ONLY`: workspace endpoints with nothing of another workspace to reach (create a
     department, edit the company profile, the local dev tools…), each with its reason;
   - `OUTSIDE_WORKSPACE`: routes with no `X-Workspace-Id` (me, create/join workspace, candidate,
     public, webhook), each with its reason and the test that covers its own access rule.
   The route's `require(action)` is read from the route itself, so the registry can't drift from
   the matrix.
2. **Coverage check** (`tests/unit/test_tenancy_coverage.py`, runs in the PR CI job): fails when a
   route is missing from the registry, listed twice, listed in the wrong group (a route that takes
   a `RequestContext` must be in `CASES` or `CALLER_ONLY`), or when an entry names a route that no
   longer exists.
3. **Tenancy suite** (`tests/tenancy/test_endpoints.py`), one parametrised test per case on a
   world in workspace A: an Engineering pipeline with applications in every stage, an integrity
   flag and a review request; the same in a Sales pipeline and a No-department pipeline; an
   invite, a member, a department and a report job.
   - Resource endpoints: every role of workspace B gets 404 for A's resource; the Engineering
     Recruiter and Hiring manager get 404 for the Sales and No-department ones (403 when their
     role may not take the action at all); the Hiring manager gets 404 for an application that is
     not shortlisted; and an allowed caller does reach the in-scope resource (so the 404s mean
     something).
   - Lists and aggregates: snapshot each response, add the data the caller must not see, and
     assert the response is unchanged: B (every role) against all of A's data; the Engineering
     Recruiter against Sales and No-department; the Hiring manager against non-shortlisted
     Engineering applications.
   - IDs from another workspace in request bodies (pipeline department, invite and member
     departments) are refused with `422 unknown_department`, and a Recruiter can't file a
     pipeline outside their departments.
4. **Web**: a vitest check that every page under `app/ta/(app)` is wrapped in `RequireAccess` (or
   `PagePlaceholder`) with the same action as its nav item in `lib/app-nav.ts`, so a page can't
   be reached by a role its nav hides. Actions on pages are already gated with `can()`.
5. Docs: MULTI_TENANCY.md §4 and DEV_WORKFLOW/AGENTS.md say how to register a new endpoint.

## Log
- 2026-10-30: branch `feature/permission-matrix-department-scoping`. Plan auto-approved (Darwin's standing rule). Picked as the last open M1 task; it unblocks CAND-001 and AVA-001.
- Audit: all 72 routes. Every TA route already had `require(action)`, and the repositories already applied departments and the shortlist (PIPE-001 onwards). The new suite found no leak in the API; planting one (dropping the shortlist filter from the profile repository, or the department filter from the analytics views) fails 6 of its checks.
- The coverage check is a unit test so it runs in the pull-request CI job, which has no database; the tenancy suite itself runs with the database suite on `develop` pushes and locally.
- Credits are workspace-wide (Recruiters read credit usage), so the Overview's `credits` card is the one value allowed to change with other departments' data.
- Web: Getting started now gates on `view_overview` like its nav item (no change for any role today).
- Board: ASMT-007 flipped to Done (merged in #57 but left Ready); M5 summary count corrected.
