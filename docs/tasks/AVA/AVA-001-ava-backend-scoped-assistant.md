# AVA-001: Ava backend (scoped assistant)

| Field | Value |
|---|---|
| Epic | AVA — Ask Ava |
| Milestone | M5 Review |
| Status | Ready |
| Size | L |
| Depends on | [ASMT-001](../ASMT/ASMT-001-interview-scoring.md), [WS-005](../WS/WS-005-permission-matrix-and-department-scoping-end-to-en.md), [FND-013](../FND/FND-013-openai-integration-layer.md) |
| Requirements | FR-AVA-01, FR-AVA-02, FR-AVA-03, FR-AVA-04, FR-AVA-05 |
| Gap areas | G2, G8 |
| Design | Frames PipelineView/CandidatePool (Ask Ava) |
| Docs to read | [`architecture/AI_PIPELINE.md §6`](../../architecture/AI_PIPELINE.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Ava answers questions about candidates with sources, strictly within what the asking member may see, and refuses unfair questions.

## Scope
**In:**
- `ava_threads`, `ava_messages` migrations
- Read-only tools over repositories taking RequestContext
- Protected-attribute pre-check + refusal
- Structured answer schema; SSE streaming endpoint
- Rate limits per member

**Out:**
- —

## Acceptance criteria
- [ ] Recruiter can't retrieve out-of-scope data via Ava (tenancy tests)
- [ ] Refuses protected-attribute questions
- [ ] Every answer lists sources
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- ai_eval Ava prompts incl. adversarial ones

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
