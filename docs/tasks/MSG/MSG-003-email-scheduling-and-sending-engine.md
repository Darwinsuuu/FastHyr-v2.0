# MSG-003: Email scheduling and sending engine

| Field | Value |
|---|---|
| Epic | MSG — Candidate emails |
| Milestone | M3 Intake |
| Status | Backlog |
| Size | M |
| Depends on | [MSG-001](../MSG/MSG-001-email-templates-model-and-defaults.md), [FND-008](../FND/FND-008-background-worker-and-job-framework.md) |
| Requirements | FR-MSG-04, FR-MSG-05, FR-MSG-06 |
| Gap areas | G1, G5 |
| Design | — |
| Docs to read | [`architecture/NOTIFICATIONS.md`](../../architecture/NOTIFICATIONS.md), [`product/WORKFLOW.md §5`](../../product/WORKFLOW.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Candidate emails go out at the right moment in the workspace's time zone and never contradict the candidate's current status.

## Scope
**In:**
- Business-day calculator (workspace tz)
- `schedule(template_key, application, at)` + cancel rules on stage change
- `dispatch_scheduled_emails` cron
- Bounce handling marks candidate email undeliverable

**Out:**
- —

## Acceptance criteria
- [ ] Rejection after override is cancelled
- [ ] Friday screening → Tuesday email (2 business days)
- [ ] Idempotent: no duplicates on retries
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
