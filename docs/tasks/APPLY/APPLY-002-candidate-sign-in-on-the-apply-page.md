# APPLY-002: Candidate sign-in on the apply page

| Field | Value |
|---|---|
| Epic | APPLY — Apply |
| Milestone | M3 Intake |
| Status | Backlog |
| Size | S |
| Depends on | [APPLY-001](../APPLY/APPLY-001-public-apply-page.md), [AUTH-001](../AUTH/AUTH-001-employer-sign-in.md) |
| Requirements | FR-APPLY-02 |
| Gap areas | — |
| Design | Frame Apply (sign-in modal, header menu) |
| Docs to read | [`decisions/ADR-014-candidate-sso-only.md`](../../decisions/ADR-014-candidate-sso-only.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Candidates sign in with Google or Microsoft without losing their place or the source tag.

## Scope
**In:**
- Sign-in modal (browse vs apply intent)
- OAuth round-trip back to the apply page with form open
- Header signed-in menu + sign out
- Note for candidates without Google/Microsoft

**Out:**
- —

## Acceptance criteria
- [ ] After sign-in with apply intent the form opens
- [ ] `source` preserved
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
