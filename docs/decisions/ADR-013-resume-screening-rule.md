# ADR-013: Résumé pass bar and nice-to-haves are set per pipeline

- **Status:** Accepted
- **Date:** 2026-09-29

## Decision
Add two fields to wizard step 1 (Role), which the canvas lacks:
- **Nice-to-haves** (optional list, hidden from candidates).
- **Résumé pass bar** (0–100, default **60**).

Résumé fit score = Must-haves 40% + Nice-to-haves 20% + Relevant experience 25% + Skill depth 15%.
A résumé **passes** when its fit score ≥ the pass bar **and** it shows related evidence for every must-have. ("Also open to" options relax the experience and must-have evidence rules as described in `architecture/AI_PIPELINE.md`.) If a pipeline has no nice-to-haves, that 20% is redistributed proportionally.

## Consequences
- Design follow-up: add the two fields to the canvas `NewPipeline` frame (spec in `design/SCREEN_SPECS.md`).
- The pass bar and weights are locked with the rest of the setup at publish.
