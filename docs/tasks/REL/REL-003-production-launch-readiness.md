# REL-003: Production launch readiness

| Field | Value |
|---|---|
| Epic | REL — Release |
| Milestone | M8 Launch readiness |
| Status | Backlog |
| Size | M |
| Depends on | [REL-002](../REL/REL-002-security-review.md), [WEB-005](../WEB/WEB-005-legal-and-ai-in-hiring-pages.md), [COMP-003](../COMP/COMP-003-candidate-data-deletion-and-retention.md) |
| Requirements | NFR-05, NFR-10 |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/DEPLOYMENT.md §6`](../../architecture/DEPLOYMENT.md), [`compliance/AI_HIRING_REGULATIONS.md (launch gates)`](../../compliance/AI_HIRING_REGULATIONS.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Production is configured, verified and ready for the first customers.

## Scope
**In:**
- Production Supabase (PITR, SMTP, OAuth verified), Stripe live, Resend domain, OpenAI limits, Sentry alerts
- Restore-from-backup drill
- Open questions OQ-1..OQ-7 resolved
- Legal launch gates checked

**Out:**
- —

## Acceptance criteria
- [ ] Launch checklist fully ticked with evidence
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
