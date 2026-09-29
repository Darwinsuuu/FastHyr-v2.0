# APPLY-003: Application submission and credit use

| Field | Value |
|---|---|
| Epic | APPLY — Apply |
| Milestone | M3 Intake |
| Status | Backlog |
| Size | L |
| Depends on | [APPLY-002](../APPLY/APPLY-002-candidate-sign-in-on-the-apply-page.md), [FND-011](../FND/FND-011-storage-service-and-pdf-handling.md), [BILL-002](../BILL/BILL-002-credit-ledger-service.md), [COMP-002](../COMP/COMP-002-notices-and-consent-versioning.md) |
| Requirements | FR-APPLY-03, FR-APPLY-04, FR-APPLY-05 |
| Gap areas | G2 |
| Design | Frame Apply (form, sent modal) |
| Docs to read | [`architecture/BILLING.md §3–4`](../../architecture/BILLING.md), [`product/WORKFLOW.md §3`](../../product/WORKFLOW.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Candidates submit a résumé and details; FastHyr records consent, uses one credit and starts screening.

## Scope
**In:**
- Form with validation and PDF upload via signed URL
- `POST /candidate/applications` (idempotent): pipeline live check, consume credit, upsert candidate, create application, store consent version, enqueue screening
- Sent modal and 'Applied on' state
- Pipeline auto-pauses when reserve runs out

**Out:**
- —

## Acceptance criteria
- [ ] One application per candidate per pipeline
- [ ] Race at last credit: only one succeeds, no credit used by the loser
- [ ] Credit ledger entry links to the application
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Use 1 credit with `services/credits.consume(session, workspace_id, pipeline_id, application_id=…)` in the same transaction as the application insert (BILL-002). It raises `pipeline_not_accepting` without using a credit.
- Add the foreign key `credit_ledger (workspace_id, application_id) → applications (workspace_id, id)`; BILL-002 left `application_id` as a plain uuid because `applications` didn't exist yet.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Concurrency test for last-credit race

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
