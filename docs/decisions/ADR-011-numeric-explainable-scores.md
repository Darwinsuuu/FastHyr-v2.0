# ADR-011: Numeric, explainable scores on TA screens

- **Status:** Accepted
- **Date:** 2026-09-29

## Context
The design system says "signals, not scores; never a single percentage", but every TA screen shows an overall score out of 100, a pass mark and the rubric math. The project instructions require explainable scoring with TA-controlled weights.

## Decision
- TA screens show **numeric scores (0–100)**: overall interview score, per-criterion scores, résumé fit score, with the weighted calculation always visible.
- **Signals** (Strong evidence / Worth probing / Not evidenced yet) label individual pieces of evidence and sub-skills, never replace the score.
- Fit badges: **Strong fit** = passed and overall ≥ 80 and all must-haves met; **Good fit** = at or above the pipeline pass mark.
- Candidates never see scores, signals or flags.

## Consequences
- The design system README's "Signals, not scores" rule is updated to this decision (`design/DESIGN_SYSTEM.md`).
