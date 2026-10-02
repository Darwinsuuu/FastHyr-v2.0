# PIPE-004: Pipelines list

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M2 Pipelines |
| Status | Ready |
| Size | M |
| Depends on | [PIPE-001](../PIPE/PIPE-001-pipeline-model-and-state-machine.md), [DASH-001](../DASH/DASH-001-app-shell.md) |
| Requirements | FR-PIPE-08 |
| Gap areas | G8 |
| Design | Frame PipelinesV2 |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users see all their pipelines, sorted so the ones that need them come first.

## Scope
**In:**
- Flow summary (week/30 days; real numbers after DASH-003, placeholder zeros before)
- Tabs, search, table, pagination
- Row menus per status (actions wired in PIPE-005)

**Out:**
- —

## Acceptance criteria
- [ ] Counts per tab correct
- [ ] Department scope applied
- [ ] Days remaining / status labels as designed
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
