# AUTH-004: Invite accept page

| Field | Value |
|---|---|
| Epic | AUTH — Authentication & workspaces |
| Milestone | M1 Access |
| Status | Ready |
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
- [ ] Wrong email, expired, revoked, already-member states handled
- [ ] Accepting applies role and departments
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- AUTH-003 built `POST /v1/invites/accept {code}` (role, departments, error codes `invite_not_found`, `invite_wrong_email`, `invite_expired`, `invite_invalid`). This task adds `{token}` accept and the `GET /invites/{code}` preview (inviter, role, departments, masked email for S-04).
- WS-004 stores `token_hash` = SHA-256 of the link token (`services/invites.new_token_hash()`); the token itself only goes into the invite email (FND-010). Resending rotates code and token on the same row. Accepted, revoked or expired invites keep their row; `expire_invites()` marks overdue ones `expired`.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
