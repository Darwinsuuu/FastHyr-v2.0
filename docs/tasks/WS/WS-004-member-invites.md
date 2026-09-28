# WS-004: Member invites

| Field | Value |
|---|---|
| Epic | WS — Workspace admin |
| Milestone | M1 Access |
| Status | Backlog |
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
- [ ] Resend invalidates the old link
- [ ] Revoked/expired invites can't be accepted
- [ ] Duplicate invite to same email replaces the previous
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
