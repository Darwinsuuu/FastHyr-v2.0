# AVA-002: Ava UI

| Field | Value |
|---|---|
| Epic | AVA — Ask Ava |
| Milestone | M5 Review |
| Status | Backlog |
| Size | M |
| Depends on | [AVA-001](../AVA/AVA-001-ava-backend-scoped-assistant.md), [PIPE-007](../PIPE/PIPE-007-pipeline-details-header-and-dashboard-tab.md), [CAND-001](../CAND/CAND-001-candidates-pool-list-and-profile-drawer.md) |
| Requirements | FR-AVA-01, FR-AVA-02, FR-AVA-05 |
| Gap areas | G2 |
| Design | Frames PipelineView/CandidatePool (Ask Ava) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users chat with Ava in the pipeline and candidates pages.

## Scope
**In:**
- Chat panel (empty state suggestions, messages with paras/table/bullets/sources/note, typing state, quick prompts, new chat)
- 'What Ava can see' and 'How Ava stays fair' side cards with live counts
- Source links open reports/recordings at timestamps

**Out:**
- —

## Acceptance criteria
- [ ] Streaming renders progressively
- [ ] Keyboard submit and accessible live region
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
