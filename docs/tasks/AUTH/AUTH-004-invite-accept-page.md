# AUTH-004: Invite accept page

| Field | Value |
|---|---|
| Epic | AUTH — Authentication & workspaces |
| Milestone | M1 Access |
| Status | In review |
| Size | S |
| Depends on | [WS-004](../WS/WS-004-member-invites.md) |
| Requirements | FR-AUTH-06 |
| Gap areas | — |
| Design | S-04 |
| Docs to read | [`design/SCREEN_SPECS.md S-04`](../../design/SCREEN_SPECS.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Invited people land on a clear page that lets the right account join the workspace.

## Scope
**In:**
- `/join/[code]` all states from S-04
- `GET /invites/{code}`, `POST /invites/accept`

**Out:**
- —

## Acceptance criteria
- [x] Wrong email, expired, revoked, already-member states handled
- [x] Accepting applies role and departments
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- AUTH-003 built `POST /v1/invites/accept {code}` (role, departments, error codes `invite_not_found`, `invite_wrong_email`, `invite_expired`, `invite_invalid`). This task adds `{token}` accept and the `GET /invites/{code}` preview (inviter, role, departments, masked email for S-04).
- WS-004 stores `token_hash` = SHA-256 of the link token (`services/invites.new_token_hash()`); the token itself only goes into the invite email (FND-010). Resending rotates code and token on the same row. Accepted, revoked or expired invites keep their row; `expire_invites()` marks overdue ones `expired`.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
**API** (`app/services/workspaces.py`, `app/api/routers/workspaces.py`)
- One lookup for both kinds of key: `find_invite(key)` treats anything that normalizes to `XXXX-XXXX` as a code, and anything else as a link token (looked up by `token_hash`, SHA-256). Codes stay case-insensitive; tokens are exact.
- `GET /v1/invites/{key}` (verified email, no workspace header): returns `InvitePreview` with a `state` the page renders: `ready` (workspace name, inviter, role, department names), `already_member` (workspace id, to redirect), `wrong_email` (only `masked_email`, e.g. `d•••@acme.com`), `expired`, `invalid`. Unknown key is `404 invite_not_found`. The email check runs first, as in accept, so a wrong account learns nothing else about the invite.
- `POST /v1/invites/accept` takes `{code}` or `{token}` (exactly one, else 422). Same rules as AUTH-003.

**Web** (site host, next to `/workspaces`, same WorkspaceSelect look)
- Extract the header, background and profile dialog of `ChooseWorkspace` into `WorkspaceSelectShell` so both pages share them.
- `app/site/join/[code]/page.tsx`: signed out goes to `/login?next=/join/{code}`; unverified to `/verify-email?next=…`. Client `JoinInvite` fetches the preview and shows one enlarged card per state: Join (workspace avatar, "{Inviter} invited you to join {Workspace} as {Role}.", department chips, "Join {Workspace}"), wrong email (masked email + Log out, which returns to `/login?next=/join/{code}`), expired, no longer valid, not found. Already a member activates the workspace and opens the app.
- `chooseDestination` keeps a `/join/…` `next` on the site host, so people with no workspace yet still land on the invite after sign-in instead of `/workspaces`.
- Messages in `messages/en.json` under `join.*`. Mobile first; checked at 360, 768, 1024, 1440.

**Tests**: API integration tests for the preview states, token accept and the code/token rule; a tenancy test that another workspace's member gets no details of an invite not addressed to them; unit test for `chooseDestination` with `/join`; one Playwright journey (invite → open link signed out → sign in → join).

## Log
- 2026-10-01: branch `feature/invite-accept-page`. Plan auto-approved (Darwin's standing rule: no plan approvals). Picked over WS-005 because WS-005 mostly filters pipelines and candidates that don't exist yet.
- Decision: the invite email link (FND-010) should be `{site}/join/{token}`; `/join/{code}` works too, so a code read out loud or a pasted link both work.
- Built as planned. Unknown links show a fourth state, "We couldn't find that invite", with a link back to Choose workspace. Expired, revoked and not-found states link to `/workspaces` so the person can still create a workspace or paste another code. `logOut(next)` now takes an optional return path, so "Log out" on the wrong-email state signs back in to the same invite.
- Screenshots: project files `screenshots/AUTH-004/` (ready at 360/768/1024/1440 light and 360/1440 dark; wrong email, expired, revoked, not found).
