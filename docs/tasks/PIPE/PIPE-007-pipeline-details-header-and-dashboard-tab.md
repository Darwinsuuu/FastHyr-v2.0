# PIPE-007: Pipeline details — header and Dashboard tab

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M5 Review |
| Status | Backlog |
| Size | M |
| Depends on | [DASH-003](../DASH/DASH-003-analytics-views-and-endpoints.md), [PIPE-004](../PIPE/PIPE-004-pipelines-list.md) |
| Requirements | FR-PIPE-11 |
| Gap areas | G1, G8 |
| Design | Frame PipelineView (Dashboard) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users see how one pipeline is performing and can re-invite people who didn't finish.

## Scope
**In:**
- Header (status, department, format, opened, owner, share)
- Tabs scaffold
- KPIs, funnel, daily chart, score histogram, sources, drop-offs
- Re-invite all with confirmation (INTV-007 API)

**Out:**
- —

## Acceptance criteria
- [ ] Numbers match analytics fixtures
- [ ] Re-invite creates new links and sends invitations
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
