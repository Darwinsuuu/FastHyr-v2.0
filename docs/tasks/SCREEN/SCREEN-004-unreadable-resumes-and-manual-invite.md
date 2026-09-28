# SCREEN-004: Unreadable résumés and manual invite

| Field | Value |
|---|---|
| Epic | SCREEN — Résumé screening |
| Milestone | M5 Review |
| Status | Backlog |
| Size | S |
| Depends on | [SCREEN-003](../SCREEN/SCREEN-003-post-screen-actions-invite-or-schedule-rejection.md), [PIPE-008](../PIPE/PIPE-008-pipeline-details-candidates-tab.md) |
| Requirements | FR-SCREEN-01 |
| Gap areas | G2 |
| Design | — |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users can handle résumés FastHyr couldn't read instead of candidates being silently dropped.

## Scope
**In:**
- 'Couldn't read résumé' badge in Candidates tab
- `POST /applications/{id}/invite-manually`
- Reject still available

**Out:**
- —

## Acceptance criteria
- [ ] Manual invite creates interview and sends invitation
- [ ] Audit logged
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
