# PIPE-002: New pipeline wizard — Role and AI interview steps

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M2 Pipelines |
| Status | Backlog |
| Size | L |
| Depends on | [PIPE-001](../PIPE/PIPE-001-pipeline-model-and-state-machine.md), [WS-002](../WS/WS-002-departments.md), [FND-012](../FND/FND-012-ui-kit-design-system-components.md) |
| Requirements | FR-PIPE-01, FR-PIPE-02 |
| Gap areas | G2, G3, G4 |
| Design | Frame NewPipeline steps 1–2 + A-01 |
| Docs to read | [`design/SCREEN_SPECS.md A-01`](../../design/SCREEN_SPECS.md), [`decisions/ADR-013-resume-screening-rule.md`](../../decisions/ADR-013-resume-screening-rule.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users describe the role, screening criteria and interview style in the first two wizard steps.

## Scope
**In:**
- Wizard shell (vertical stepper, Save as draft, Cancel, Back/Continue with blocking hints)
- Step 1 fields incl. nice-to-haves and résumé pass bar
- Step 2 fields and toggles
- Draft autosave on step change

**Out:**
- Steps 3–5 (PIPE-003)

## Acceptance criteria
- [ ] Min-3 rules for must-haves and skills enforced with the designed messages
- [ ] Draft reload restores all fields
- [ ] Department list comes from the workspace
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Fairness hint text under must-haves as designed

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Functional: min-3 must-haves/skills rule blocks Continue; draft save and reload keeps all fields

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
