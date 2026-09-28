# APPLY-001: Public apply page

| Field | Value |
|---|---|
| Epic | APPLY — Apply |
| Milestone | M3 Intake |
| Status | Backlog |
| Size | M |
| Depends on | [PIPE-001](../PIPE/PIPE-001-pipeline-model-and-state-machine.md), [WS-001](../WS/WS-001-company-profile.md), [FND-012](../FND/FND-012-ui-kit-design-system-components.md) |
| Requirements | FR-APPLY-01, FR-APPLY-06 |
| Gap areas | G2 |
| Design | Frame Apply |
| Docs to read | [`architecture/API.md (public)`](../../architecture/API.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Anyone with the apply link sees a clear, branded job page with the right status.

## Scope
**In:**
- `GET /public/pipelines/{ws}/{slug}` (candidate-safe fields only)
- Page sections as designed; mobile layout
- Status banners: accepting/closes, opens on, not taking applications, closed; 404 for draft/cancelled
- Source tag captured from URL and kept through sign-in

**Out:**
- Sign-in and form (APPLY-002/003)

## Acceptance criteria
- [ ] Hidden fields (must-haves, skills, rubric) never returned by the public endpoint (test)
- [ ] Lighthouse accessibility ≥ 95
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
