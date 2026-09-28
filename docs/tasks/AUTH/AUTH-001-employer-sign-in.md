# AUTH-001: Employer sign-in

| Field | Value |
|---|---|
| Epic | AUTH — Authentication & workspaces |
| Milestone | M1 Access |
| Status | Backlog |
| Size | M |
| Depends on | [FND-005](../FND/FND-005-web-skeleton-hosts-tokens-fonts-auth-session-api-c.md), [FND-012](../FND/FND-012-ui-kit-design-system-components.md) |
| Requirements | FR-AUTH-01, FR-AUTH-04, FR-AUTH-09 |
| Gap areas | — |
| Design | Frame EmployerLogin |
| Docs to read | [`design/SCREENS.md`](../../design/SCREENS.md), [`architecture/SECURITY.md §1`](../../architecture/SECURITY.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users can sign in with Google, Microsoft or email + password and land in the right place.

## Scope
**In:**
- `/login` page as designed (split layout)
- OAuth + email/password via Supabase; `/auth/callback`
- Post-login routing (workspaces vs last active workspace; `next` param)
- Log out

**Out:**
- Password reset (AUTH-002)

## Acceptance criteria
- [ ] Each method signs in and routes correctly
- [ ] Errors shown inline (wrong password, provider cancelled)
- [ ] Terms/Privacy links present
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- "New here?" — first sign-in creates the account

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Playwright: email sign-in happy path

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
