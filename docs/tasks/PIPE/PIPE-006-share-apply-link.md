# PIPE-006: Share apply link

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M2 Pipelines |
| Status | Ready |
| Size | S |
| Depends on | [PIPE-001](../PIPE/PIPE-001-pipeline-model-and-state-machine.md) |
| Requirements | FR-PIPE-10 |
| Gap areas | G8 |
| Design | Frame PipelinesV2 / PipelineView (share modal) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users copy a tagged apply link for each job board with the right posting hint.

## Scope
**In:**
- Share modal component (8 sources, copied state, hints)
- `GET /pipelines/{id}/share-links`

**Out:**
- —

## Acceptance criteria
- [ ] Copied URL format `…/apply/{ws}/{slug}?source={id}`
- [ ] Works for scheduled pipelines too
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- PIPE-003 built the tiles: `ShareTiles` in `apps/web/components/pipelines/share-tiles.tsx` (8 sources, copied state, each board's hint) and `applyLink()` in `lib/pipelines/wizard.ts`. Wrap it in the share modal rather than building a second set.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
