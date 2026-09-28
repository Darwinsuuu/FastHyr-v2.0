# PIPE-001: Pipeline model and state machine

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M2 Pipelines |
| Status | Backlog |
| Size | M |
| Depends on | [FND-003](../FND/FND-003-core-schema-identity-workspaces-members-department.md), [FND-008](../FND/FND-008-background-worker-and-job-framework.md), [BILL-002](../BILL/BILL-002-credit-ledger-service.md) |
| Requirements | FR-PIPE-07, FR-PIPE-15 |
| Gap areas | G3, G4 |
| Design | — |
| Docs to read | [`product/WORKFLOW.md §2`](../../product/WORKFLOW.md), [`architecture/DATABASE.md (pipelines)`](../../architecture/DATABASE.md), [`architecture/BILLING.md §3`](../../architecture/BILLING.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Pipelines exist in the database with their full setup, a strict state machine, locking and scheduled open/close.

## Scope
**In:**
- `pipelines` migration incl. lock trigger
- `services/pipelines.py`: create draft, update draft, publish (reserve credits), start now, pause, resume, close (release), cancel (release), archive, duplicate
- Cron: open scheduled, close due
- Slug generation (unique per workspace, fixed after publish)
- Audit entries

**Out:**
- UI (PIPE-002..)

## Acceptance criteria
- [ ] Every transition in WORKFLOW.md §2 covered by tests; invalid ones raise `invalid_transition`
- [ ] Locked setup cannot change (DB trigger + service check)
- [ ] Closing releases unused reserve via credits service
- [ ] Scheduled pipeline opens within 1 min of `opens_at`
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Pausing never extends closes_at

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- State-machine table-driven tests

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
