# AUTH-002: Password reset and email verification

| Field | Value |
|---|---|
| Epic | AUTH — Authentication & workspaces |
| Milestone | M1 Access |
| Status | Backlog |
| Size | S |
| Depends on | [AUTH-001](../AUTH/AUTH-001-employer-sign-in.md), [FND-010](../FND/FND-010-email-infrastructure-resend.md) |
| Requirements | FR-AUTH-02, FR-AUTH-03 |
| Gap areas | — |
| Design | Frame EmployerLogin (modal), S-05, S-06 |
| Docs to read | [`design/SCREEN_SPECS.md S-05, S-06`](../../design/SCREEN_SPECS.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Password users can recover access and must verify their email before using a workspace.

## Scope
**In:**
- Forgot-password modal states (form, sending, sent, resend 60 s)
- `/reset-password` (S-05)
- `/verify-email` (S-06)
- Supabase email templates via Resend SMTP

**Out:**
- —

## Acceptance criteria
- [ ] Reset link single-use, 1 h expiry
- [ ] Response never reveals whether an email exists
- [ ] Unverified users can't create/join workspaces
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
