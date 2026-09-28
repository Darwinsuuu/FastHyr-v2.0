# ADR-017: Manual "Advance" action

- **Status:** Accepted
- **Date:** 2026-09-29

## Context
The canvas has only "Reject", and the "Moving to the next stage" email sends automatically when a candidate passes. Multi-stage pipelines and scheduling are out of MVP.

## Decision
- Add an **Advance to next round** action (candidate row menu and candidate profile header) for candidates in **Ready for review** or **Flagged** (after flags are reviewed).
- Advancing sets the stage to **Advanced**, asks for an optional note, and sends the **Moving to the next stage** email (the TA user can untick it).
- The "Moving to the next stage" template is **no longer sent automatically** on pass.
- Scheduling the human interview stays outside FastHyr (the email can include the team's booking link as text).

## Consequences
- New UI specified in `design/SCREEN_SPECS.md`. Hiring managers cannot advance in MVP (ADR-005).
