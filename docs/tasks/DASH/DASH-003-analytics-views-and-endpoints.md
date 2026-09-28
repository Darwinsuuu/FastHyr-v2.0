# DASH-003: Analytics views and endpoints

| Field | Value |
|---|---|
| Epic | DASH — Dashboard |
| Milestone | M5 Review |
| Status | Backlog |
| Size | M |
| Depends on | [PIPE-001](../PIPE/PIPE-001-pipeline-model-and-state-machine.md), [APPLY-003](../APPLY/APPLY-003-application-submission-and-credit-use.md), [INTV-007](../INTV/INTV-007-interview-lifecycle-resume-expiry-reminders-re-inv.md), [ASMT-001](../ASMT/ASMT-001-interview-scoring.md) |
| Requirements | FR-DASH-02, FR-DASH-04, FR-PIPE-11, FR-CAND-03 |
| Gap areas | G8, G1 |
| Design | Frames Overview, PipelinesV2, PipelineView, CandidatePool |
| Docs to read | [`architecture/DATABASE.md §4`](../../architecture/DATABASE.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
One analytics layer computes funnels, time-to-screen, sources and drop-offs for every dashboard, scoped by role.

## Scope
**In:**
- SQL views (`v_pipeline_funnel`, `v_source_stats`, `v_dropoff_reasons`, `v_time_to_screen`)
- `services/analytics.py` + endpoints used by Overview, Pipelines flow, pipeline dashboard, candidates dashboard

**Out:**
- —

## Acceptance criteria
- [ ] Numbers match hand-computed fixtures
- [ ] Department scope applied
- [ ] p95 < 400 ms on seed data
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
