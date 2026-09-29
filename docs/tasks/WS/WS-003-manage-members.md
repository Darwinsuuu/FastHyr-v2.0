# WS-003: Manage members

| Field | Value |
|---|---|
| Epic | WS — Workspace admin |
| Milestone | M1 Access |
| Status | Done |
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
- [x] Owner cannot be removed/demoted
- [x] Changes take effect on next request
- [x] last_active_at updated (throttled)
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- The owner is always an Admin and can't be changed or removed. Admins can't change or remove their own access either, so nobody locks themselves out; neither row has an actions menu.
- Admins see every department, so their departments are cleared and shown as "All departments". Recruiters and Hiring managers may have none ("No departments yet").
- Removing a member keeps the row (status `removed`) and drops their departments; accepting a new invite reactivates it with the invite's role (AUTH-003 already does this).
- "Last active" is relative ("Now" under 5 minutes, minutes, hours, "Yesterday", days) and a date after 30 days; "Not yet" if they never made a workspace request.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
Size M: approved by the product owner on 2026-09-29.

**Database** (one migration)
- `profiles.email`: the list shows each member's email, which lives only in `auth.users`. A trigger copies it on sign-up and on email change; the migration backfills existing rows. The API keeps no access to the `auth` schema.

**API** (`GET /v1/members`, `PATCH /v1/members/{id}`, `DELETE /v1/members/{id}`, Admin only via `require(manage_workspace)`)
- `routers/members.py` → `services/members.py` → `repositories/members.py` (workspace-scoped; other workspaces' members are 404).
- `GET` returns every active member: name, email, avatar, role, owner flag, department IDs and names, last active, status, plus `is_you`.
- `PATCH {role?, department_ids?}`: Admins get "All departments", so switching to Admin clears their departments; unknown department IDs are 422. `DELETE` sets status `removed` and drops their departments; an invite brings them back later (already handled by `POST /invites/accept`).
- Rules: the owner can't be changed or removed (`409 owner_access_locked`); an Admin can't change or remove themselves (`409 own_access_locked`), so nobody locks themselves out.
- Changes apply on the next request, because `RequestContext` already loads role and departments per request. A removed member gets `403 not_a_member` straight away.
- `last_active_at`: `get_request_context` writes it only when it is empty or older than 5 minutes (throttled).
- Audit rows: `member.access_changed` (from/to role and departments) and `member.removed`.

**Web** (`/settings/members`, `RequireAccess manage_workspace`)
- Header, Members list with search (name or email), role filter, multi-select department filter, count, table (member, role, departments, last active, status, actions menu) with phone cards below `md`, and pagination (10/25/50). Filtering and paging are client-side, like Departments, since a workspace has tens of members.
- Edit access dialog (role select and department multi-select, disabled with "All departments" for Admins), Remove access confirm, "What each role can do" card. Owner and "you" rows have no actions.
- Invite button and Pending invites tab are left out until WS-004.
- Logic (filters, relative "last active") in `lib/members`.

**Tests** (after testing by hand): API integration + tenancy for the three endpoints, owner/self rules, next-request effect, last-active throttle; web unit tests for filters and last-active text.

## Log
- 2026-09-29: branch `feature/member-management-yflnb4`. The Invite button and Pending invites tab are left for WS-004, so the page shows the Members list without tabs. Department pickers are a checkbox list (inside the dialog; in a popover for the filter) rather than the frame's chip dropdown, which reads better on phones. Screenshots in the project's `screenshots/WS-003/`.
