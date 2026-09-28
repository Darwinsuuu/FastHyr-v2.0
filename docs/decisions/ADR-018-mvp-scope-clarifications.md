# ADR-018: MVP scope clarifications

- **Status:** Accepted
- **Date:** 2026-09-29

## Decisions
1. **Public job board ("Find Jobs") is post-MVP.** Candidates reach FastHyr only through a pipeline's apply link. The "For candidates" page ships as a marketing page without listings; the "Find Jobs" nav item becomes "For candidates".
2. **Ava is the TA assistant only.** The interviewer is "the AI interviewer" everywhere (reports, transcripts, marketing copy).
3. **Missing screens are specified in the docs** (`design/SCREEN_SPECS.md`) as text wireframes in the existing style, not designed in Claude Design first.
4. **Claude builds the MVP.** Cursor is not used in this iteration; Claude (Claude Code) plans, implements and reviews (`process/DEV_WORKFLOW.md`).
5. **Out of MVP:** multi-stage pipelines, human-interview scheduling, in-app notifications, job board, multi-language interviews, ATS/HRIS integrations (never planned), multi-region data residency.
