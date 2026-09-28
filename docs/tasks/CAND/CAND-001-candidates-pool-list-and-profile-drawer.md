# CAND-001: Candidates pool — list and profile drawer

| Field | Value |
|---|---|
| Epic | CAND — Candidates pool |
| Milestone | M5 Review |
| Status | Backlog |
| Size | M |
| Depends on | [ASMT-001](../ASMT/ASMT-001-interview-scoring.md), [WS-005](../WS/WS-005-permission-matrix-and-department-scoping-end-to-en.md) |
| Requirements | FR-CAND-01, FR-CAND-02, FR-CAND-04 |
| Gap areas | G8 |
| Design | Frame CandidatePool (list, drawer) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users see everyone who has applied to the workspace and each person's history.

## Scope
**In:**
- `GET /candidates`, `GET /candidates/{id}`
- Filters, search (name/email/skill), pagination
- Drawer: stats, latest assessment, score over time, Ava summary (from ASMT data), skills, application history links
- View-only notice

**Out:**
- —

## Acceptance criteria
- [ ] Scope rules applied (HM shortlist only)
- [ ] Returning badge when > 1 application
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
