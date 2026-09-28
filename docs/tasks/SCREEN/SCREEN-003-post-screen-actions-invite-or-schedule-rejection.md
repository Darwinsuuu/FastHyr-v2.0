# SCREEN-003: Post-screen actions: invite or schedule rejection

| Field | Value |
|---|---|
| Epic | SCREEN — Résumé screening |
| Milestone | M3 Intake |
| Status | Backlog |
| Size | M |
| Depends on | [SCREEN-002](../SCREEN/SCREEN-002-resume-assessment-and-decision.md), [MSG-003](../MSG/MSG-003-email-scheduling-and-sending-engine.md), [INTV-001](../INTV/INTV-001-interview-plan-generation.md) |
| Requirements | FR-SCREEN-05 |
| Gap areas | G1, G5 |
| Design | — |
| Docs to read | [`product/WORKFLOW.md §3`](../../product/WORKFLOW.md), [`architecture/NOTIFICATIONS.md`](../../architecture/NOTIFICATIONS.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Passing candidates are invited to interview automatically; others get a kind rejection with a review route at the right time.

## Scope
**In:**
- On pass: plan interview → create interview (token, expiry) → invitation email
- On fail: stage `resume_not_match`, schedule `reject_resume` (2 business days) if enabled, with review link
- Stage polling visible in UI

**Out:**
- —

## Acceptance criteria
- [ ] Invitation contains a working personal link
- [ ] Rejection email includes `[Review.link]`
- [ ] Toggle off → no email
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
