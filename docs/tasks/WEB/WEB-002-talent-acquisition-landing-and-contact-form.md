# WEB-002: Talent acquisition landing and contact form

| Field | Value |
|---|---|
| Epic | WEB — Public website |
| Milestone | M7 Public site & demo |
| Status | Backlog |
| Size | M |
| Depends on | [FND-012](../FND/FND-012-ui-kit-design-system-components.md), [FND-010](../FND/FND-010-email-infrastructure-resend.md) |
| Requirements | FR-WEB-01, FR-WEB-02 |
| Gap areas | — |
| Design | Frame TalentAcquisition |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Employers see how FastHyr works and can contact the team.

## Scope
**In:**
- Page sections incl. animated example
- Contact form → `POST /public/contact` (rate limit, bot check, email to hello@)
- 'Start a chat' hidden or mailto in MVP

**Out:**
- —

## Acceptance criteria
- [ ] Form stores and emails
- [ ] Reduced motion respected
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
