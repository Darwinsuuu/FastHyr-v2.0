# ADR-015: Automated rejections stay, with a human-review offer and a decision log

- **Status:** Accepted
- **Date:** 2026-09-29

## Context
The design sends "Not moving forward" emails automatically after the résumé screen and after an interview below the pass mark. Under GDPR Art. 22 and several AI-hiring laws, a decision with significant effect made only by automated means needs safeguards.

## Decision
- Automatic rejection emails remain (pipeline toggles in wizard step 3).
- Every automated rejection email includes a **"Request a human review"** link. The request:
  - marks the application **Review requested**, shows it in the pipeline's Candidates tab (filter + badge) and in Overview → Needs your attention;
  - emails the pipeline owner;
  - is acknowledged to the candidate by email.
- A recruiter resolves it: **Uphold** (with a note) or **Override** (résumé → Invited to interview; interview → Ready for review).
- Every AI decision (résumé pass/fail, interview pass/fail, integrity flags) is written to an append-only **`ai_decisions`** log with inputs reference, model, prompt version, output and time.

## Consequences
- New UI elements not in the canvas are specified in `design/SCREEN_SPECS.md`.
- Candidate notices state that AI is used, that a person makes final hiring decisions, and how to request a review.
