# WS-004: Member invites

| Field | Value |
|---|---|
| Epic | WS — Workspace admin |
| Milestone | M1 Access |
| Status | Done |
| Size | M |
| Depends on | [WS-003](../WS/WS-003-manage-members.md), [FND-010](../FND/FND-010-email-infrastructure-resend.md) |
| Requirements | FR-WS-03 |
| Gap areas | — |
| Design | Frame ManageMembers (invite modal, pending tab) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Admins invite teammates by email with a role and departments; invites can be resent or revoked.

## Scope
**In:**
- Invite modal
- Pending invites tab (expiry, resend, revoke dialogs)
- Invite email with link + code
- 7-day expiry cron

**Out:**
- —

## Acceptance criteria
- [x] Resend invalidates the old link
- [x] Revoked/expired invites can't be accepted
- [x] Duplicate invite to same email replaces the previous
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Built before FND-010 (email) and FND-008 (worker) with Darwin's OK (2026-09-29): the invite is created, resent and revoked as specified, and the admin gets the code with a ready-to-send message to copy. `services/invites.send_invite_email()` is the one place FND-010 fills in; `services/invites.expire_invites()` is the job FND-008 registers as a cron. Until then, `POST /invites/accept` already refuses an invite past its `expires_at`.
- The invite code is `XXXX-XXXX` from an alphabet without look-alike characters (no 0/O, 1/I/L). Resending rotates the code and token on the same row, so the old code reads as "not found".
- Inviting an email that already has a pending invite (even one past its expiry the cron hasn't swept yet) replaces that invite: new role, departments, code and 7-day expiry. Inviting someone who is already an active member is `409 already_a_member`; a removed member can be invited back.
- `sent_at` is derived as `expires_at − 7 days` (every send and resend sets a fresh 7-day expiry), so no new column.
- The link in the invite email (`/join/<code>`) is AUTH-004's page; until it exists the copied message points people to Join a workspace, which accepts the code or the pasted link.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
Size M: plan auto-approved (Darwin's standing rule, 2026-09-29).

**API** (`GET/POST /v1/invites`, `POST /v1/invites/{id}/resend`, `DELETE /v1/invites/{id}`; Admin only via `require(manage_workspace)`)
- `routers/invites.py` → `services/invites.py` → `repositories/invites.py` (workspace-scoped: other workspaces' invites are 404).
- `GET` lists pending invites that haven't expired, newest first: email, role, departments (names; ones deleted since are dropped), inviter name, `sent_at`, `expires_at`, `code`.
- `POST {email, role, department_ids}`: email normalised to lower case; Admins get no departments; unknown departments `422 unknown_department`; an active member with that email `409 already_a_member`; an existing pending invite for the email is replaced in place (the unique pending index allows only one). Returns the invite with its code (`201`).
- `resend`: pending invites only; new code, new token hash, expiry reset to 7 days, inviter becomes the caller. `DELETE`: status `revoked` (`204`).
- Code and token: `secrets` random; only the token's SHA-256 is stored (SECURITY.md). Emails and codes never go into logs.
- Audit rows: `member.invited` (role, departments, `replaced` flag), `member.invite_resent`, `member.invite_revoked`; no email in audit data (entity is the invite ID).
- `send_invite_email()` no-op hook for FND-010; `expire_invites(session)` flips pending invites past `expires_at` to `expired`, for FND-008's cron.

**Web** (`/settings/members`)
- Header "Invite members" button; Members and Pending invites tabs with counts (UI kit `Tabs`).
- Pending invites list per the frame: email, "Invited as {role} · sent {when}", Pending status with expiry ("Expires in 3 days", amber at 2 days or less), Copy code, Resend, Revoke; phone cards below `md`; client-side pagination 10/25/50; "No pending invites." empty state.
- Invite dialog (email, role, departments checklist as in Edit access, role hint) → on success it turns into "Invite ready" with the code and a copyable message. Resend dialog ("Reinvite {email}?", current vs new expiry) → same share view. Revoke confirm ("Keep invite" / "Revoke invite").
- Logic (expiry and sent text, share message, error keys, email check) in `lib/invites`.

**Tests** (after testing by hand): API integration + tenancy for the four endpoints, replace-on-duplicate, resend invalidates the old code, revoked/expired can't be accepted, `expire_invites`; web unit tests for `lib/invites`; e2e invite → pending → resend → revoke.

## Log
- 2026-09-29: branch `feature/invites-p2zy58`. Plan auto-approved per Darwin's standing rule. Built ahead of FND-010 and FND-008 with Darwin's OK: no email is sent yet, so the invite dialog shows the code and a message to copy instead of "They'll get an email".
