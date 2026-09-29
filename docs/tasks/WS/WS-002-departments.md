# WS-002: Departments

| Field | Value |
|---|---|
| Epic | WS — Workspace admin |
| Milestone | M1 Access |
| Status | In review |
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
- [x] Deleting a department moves its pipelines to No department and removes member access
- [x] Counts correct
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Names are 1–40 characters (frame), descriptions up to 120; unique per workspace ignoring case; "No department" (any case or spacing) is reserved.
- Pipeline counts leave out drafts, which the Pipelines list doesn't show (WORKFLOW.md §2). "Active" is live or paused; "closed" is closed or cancelled.
- Candidates show "—" until APPLY-003 adds applications; the API already returns `candidate_count` (always 0 for now).
- The frame's page is Admin-only. `GET /departments` still serves every member (names for pickers and filters), but only Admins get counts, members and No department.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Tenancy tests

## Implementation plan
Size S, so built without a separate approval (DEV_WORKFLOW.md step 2).
- Migration: `pipelines.department_id` (null = No department) with a composite FK to `departments (workspace_id, id)` and no ON DELETE action, plus an index.
- API: `GET/POST /v1/departments`, `PATCH/DELETE /v1/departments/{id}` (read: member, write: Admin) in `routers/departments.py` → `services/departments.py` → `repositories/departments.py`. Delete moves pipelines to No department, drops the ID from pending invites, and cascades `member_departments`. Audit rows for created, renamed and deleted (`repositories/audit.py`).
- Errors: `409 department_name_taken`, `422 department_name_reserved`.
- Web: `/settings/departments` in the app shell (`RequireAccess manage_workspace`): summary tiles, search, table with phone cards, client-side pagination, add/edit dialog, delete confirm, info note. Logic in `lib/departments`.
- Tests: API integration + tenancy (`tests/integration/test_departments.py`), web unit tests for name rules, search and counts.

## Log
- 2026-09-29: branch `feature/departments`. Search and pagination are client-side (a workspace has few departments). "View its pipelines" links to `/pipelines?department=<id>` for PIPE-004 to read. Screenshots in the project's `screenshots/WS-002/`.
