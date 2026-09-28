# COMP-003: Candidate data deletion and retention

| Field | Value |
|---|---|
| Epic | COMP — Compliance |
| Milestone | M8 Launch readiness |
| Status | Backlog |
| Size | M |
| Depends on | [CAND-001](../CAND/CAND-001-candidates-pool-list-and-profile-drawer.md), [FND-011](../FND/FND-011-storage-service-and-pdf-handling.md) |
| Requirements | FR-COMP-05 |
| Gap areas | — |
| Design | A-05 |
| Docs to read | [`compliance/PRIVACY.md §4–5`](../../compliance/PRIVACY.md), [`design/SCREEN_SPECS.md A-05`](../../design/SCREEN_SPECS.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Admins can erase a candidate completely, and old data is purged automatically.

## Scope
**In:**
- Delete candidate data dialog + endpoint + job
- `deletion_requests`
- `retention_purge` cron (recordings 12 m, candidates 24 m)
- Storage reconciliation

**Out:**
- —

## Acceptance criteria
- [ ] After deletion no row/object references the candidate except the deletion record
- [ ] Aggregates unchanged
- [ ] Completes within minutes
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
