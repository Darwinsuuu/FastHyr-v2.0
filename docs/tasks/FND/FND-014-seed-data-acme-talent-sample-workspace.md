# FND-014: Seed data: Acme Talent sample workspace

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | Backlog |
| Size | S |
| Depends on | [FND-003](../FND/FND-003-core-schema-identity-workspaces-members-department.md) |
| Requirements | — |
| Gap areas | — |
| Design | All frames (sample data) |
| Docs to read | [`architecture/DATABASE.md §5`](../../architecture/DATABASE.md), [`_sources/design-canvas-inventory.md`](../../_sources/design-canvas-inventory.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Local, development and QA databases contain the design's sample workspace so screens can be built against realistic data.

## Scope
**In:**
- `supabase/seed.sql` (and a Python seeder for later tables, extended by each epic)
- Acme Talent, departments, members, pipelines in each status

**Out:**
- —

## Acceptance criteria
- [ ] `make db-reset` yields a workspace matching the design's sample numbers roughly
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Synthetic people only; extend the seeder as tables are added (each task updates it)

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
