# INTV-002: Interview link page and states

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M4 AI interview |
| Status | Backlog |
| Size | M |
| Depends on | [SCREEN-003](../SCREEN/SCREEN-003-post-screen-actions-invite-or-schedule-rejection.md), [APPLY-002](../APPLY/APPLY-002-candidate-sign-in-on-the-apply-page.md) |
| Requirements | FR-INTV-02 |
| Gap areas | G1, G7 |
| Design | S-01 |
| Docs to read | [`design/SCREEN_SPECS.md S-01`](../../design/SCREEN_SPECS.md), [`decisions/ADR-014-candidate-sso-only.md`](../../decisions/ADR-014-candidate-sso-only.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Candidates opening their interview link always see the right next step.

## Scope
**In:**
- `interviews` migration (token hash, status, expiry…)
- `GET /candidate/interviews/{token}` with state resolution
- `/interview/[token]` page with every S-01 state
- Same-account check

**Out:**
- Device check (INTV-003)

## Acceptance criteria
- [ ] Each S-01 state reachable in tests
- [ ] Token lookup is constant-time on hash
- [ ] Masked email shown on sign-in state
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
