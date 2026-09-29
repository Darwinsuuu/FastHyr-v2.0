# FND-010: Email infrastructure (Resend)

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | Backlog |
| Size | M |
| Depends on | [FND-008](../FND/FND-008-background-worker-and-job-framework.md) |
| Requirements | FR-MSG-04, FR-MSG-06 |
| Gap areas | G5 |
| Design | — |
| Docs to read | [`architecture/NOTIFICATIONS.md`](../../architecture/NOTIFICATIONS.md), [`decisions/ADR-008-resend-for-email.md`](../../decisions/ADR-008-resend-for-email.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
The API can render a branded email, log it and send it through Resend, with delivery status coming back by webhook.

## Scope
**In:**
- `email_messages` migration
- `services/emails.py`: render (Jinja2 layout + sanitised body + params), schedule, send job
- Resend client wrapper + webhook endpoint with signature check
- Dev mode: log/preview emails instead of sending

**Out:**
- Workspace templates (MSG-001)
- Business-day scheduling (MSG-003)

## Acceptance criteria
- [ ] System email (e.g. test) sends on the development environment and status updates to delivered
- [ ] HTML sanitised with allow-list
- [ ] Plain-text alternative generated
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Sender name `{Company} via FastHyr`
- Member invite email: fill in `services/invites.send_invite_email(invite, token)` (WS-004 calls it on invite and resend; link `/join/<code>` plus the code, 7-day expiry). Then change the invite dialog copy in `messages/en.json` (`members.invites.inviteDialog.body`, `shareDialog`) to say the email was sent, as the ManageMembers frame does.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Unit tests for rendering and sanitising

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
