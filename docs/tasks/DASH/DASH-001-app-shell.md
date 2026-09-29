# DASH-001: App shell

| Field | Value |
|---|---|
| Epic | DASH — Dashboard |
| Milestone | M1 Access |
| Status | In review |
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
- [x] Matches frames
- [x] Hidden items also blocked by API
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- The switcher calls `useSwitchWorkspace()` (`lib/api/provider.tsx`, AUTH-003): it sets the `fh_ws` cookie, saves the last workspace (`PUT /v1/me/last-workspace`) and clears the query cache. Create and Join can link to `/workspaces` on the site host, which lists the user's workspaces above the create and join cards.
- AUTH-003 added a placeholder app `/getting-started` (new workspaces open there); DASH-002 replaces it.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
Branch: `feature/app-shell-h9gkpo` from `develop` (FND-012, AUTH-003 and BILL-002 merged).

**Layout** (`components/app-shell/`, used by `app/ta/layout.tsx` for every app page except `/dev/ui` and `sign-in-required`)
- From `lg`: the frame's 264 px sidebar (surface-raised, right border) beside a scrolling `main`: logo, workspace switcher button, nav, user button at the bottom.
- Below `lg`: a sticky top bar with a menu button, the workspace name (opens the switcher) and the user's avatar (opens the user menu). The menu button opens the same sidebar as a full-height drawer from the left (Radix Dialog: focus trapped, Escape and scrim close it, closes on navigation).
- Nav as in the frames: Getting started, Overview, Pipelines, Candidates; **Billing & usage**: Billing & invoices, Credit usage; **Workspace admin**: Company profile, Departments, Manage members, Email templates. Active item uses the frame's selected style (`aria-current="page"`, matched by path prefix). Icons from Phosphor, the set the UI kit already uses.

**Role-aware nav** (`lib/permissions.ts`, mirroring `app/core/permissions.py` and the FRONTEND.md route map)
- Admin sees everything. Recruiter: the four main items, Credit usage (read-only) and Email templates. Hiring manager: the four main items only. A section heading with no visible items is hidden.
- Opening a hidden route by URL shows an "You don't have access to this page" empty state, not the page. The real guard is the API: every endpoint behind these pages calls `require(action)` with the matching `Action`, so a hidden page's data returns 403/404 whatever the UI does. This task adds a unit test pinning the nav-to-action table to the API matrix for each role (both sides), so the two can't drift silently.

**Pages that don't exist yet**
- Every nav route gets a thin placeholder page (title plus "This page is on its way") so the shell can be clicked through; the task that builds each page replaces its file. App `/` redirects to `/overview`. The `/getting-started` placeholder keeps its heading and loses its own Log out button (the shell has it). The old "signed in as" panel on `/` is removed.
- Default I'm picking: link all items now rather than hiding unbuilt ones. FRONTEND.md's "unfinished screens are simply not linked" is about launch; before launch every item is linked so the shell matches the frames.

**Workspace switcher** (FR-AUTH-07)
- Button: workspace initial tile, "Workspace" eyebrow, name, chevron. Opens a popover from `md` and a bottom sheet on phones (as the UI kit's `Menu` does).
- Lists every workspace from `GET /v1/me/workspaces` with "{Role} · {N} members", a check on the active one; then **Create a workspace** ("Start fresh for a new company or team") and **Join a workspace** ("Use an invite link or code"), both opening `/workspaces` on the site host.
- Choosing another workspace calls `useSwitchWorkspace()` (cookie, last workspace, cache cleared) and goes to the same section's top page in the new workspace (for example `/pipelines/…` → `/pipelines`), or `/overview` if the new role can't see that section.
- No valid active workspace (no cookie, or the user was removed from it): the shell sends the user to `/auth/continue?next=<path>`, which already picks the last or first workspace, or `/workspaces` when they have none.

**User menu**
- Button: avatar initials, name, email (truncated). Menu: name, "{Role} · {Workspace}", then **Log out** (existing `logOut()`). "User profile" and its modal are AUTH-005.

**Copy and styles**: all copy in `messages/en.json`; tokens and UI kit only; Paper and Night; mobile first, checked at 360, 768, 1024 and 1440 px, screenshots in the project files.

**Tests (after it works)**
- Web unit: nav visibility per role, active-item matching, switch destination path.
- API unit: the nav actions (billing, credit usage, company profile/departments/members, email templates) are allowed and denied per role exactly as the nav shows them.
- Playwright: sign in → create two workspaces → switch from the sidebar lands in the other workspace; phone viewport opens the drawer and the switcher sheet.
- No new endpoints, so no new tenancy test.

**Board:** BILL-002 Done, DASH-001 In review.

## Log
- 2026-09-29: branch `feature/app-shell-h9gkpo`. The owner approved the plan.
- **Route group.** App pages live in `app/ta/(app)/` under a layout that wraps them in `AppShell`; `/dev/ui` and `sign-in-required` stay outside it. The layout reads `fh_ws` on the server and the shell checks it against `GET /v1/me/workspaces`; with no valid workspace it hands over to `/auth/continue?next=<path>`.
- **Placeholders.** Every nav route has a `PagePlaceholder` ("This page is on its way") naming the task that replaces it. App `/` redirects to `/overview`. The old signed-in panel on `/` is gone.
- **Hidden pages.** `lib/permissions.ts` mirrors `app/core/permissions.py`; `lib/app-nav.ts` maps each nav item to its `Action`. A hidden page opened by URL shows "You don't have access to this page" (`RequireAccess`). The API test `tests/unit/test_web_permissions_mirror.py` fails if the web table drifts from `MATRIX`, and each page's endpoints call `require()` with the same action, so the API blocks what the nav hides.
- **Departments is Admin-only in the nav** (FRONTEND.md route map), although every role may *view* departments through the API (department pickers and filters).
- **Switching** calls `useSwitchWorkspace()` then does a full page load to the same section's top page (`switchDestination`), or `/overview` if the new role can't see it. A full load keeps the cache reset simple and re-reads the cookie on the server.
- **User menu** has the name, "{Role} · {Workspace}" and Log out; "User profile" and the account modal stay in AUTH-005. When a user has no name, the email shows once.
- Screenshots: project files `screenshots/DASH-001/` (360, 768, 1024, 1440; Paper and Night; admin, recruiter and hiring-manager views).
