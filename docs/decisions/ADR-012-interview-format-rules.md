# ADR-012: Adaptive interview with a 30-minute cap, English only

- **Status:** Accepted
- **Date:** 2026-09-29

## Decision
- Every interview is **adaptive**: no fixed question count and no per-question timer.
- A session has a **hard cap of 30 minutes** (platform setting, not per pipeline). The interviewer starts wrapping up at 25 minutes. The candidate sees a "Time remaining" indicator.
- **English only** in MVP.
- The **pipeline wizard's settings are canonical**: format (video + voice / voice only), tone (Warm, Professional, Direct), seniority (Entry, Mid-level, Senior, Lead), skills to probe. The demo's extra personas, 7 tones and language picker are removed; the demo uses the same settings as the wizard.
- The public demo interview is capped at **10 minutes** (config) to control cost.

## Consequences
- Candidate-facing copy "6–10 questions" and "Question 3 of 8" is removed; say "about 20–30 minutes".
- Multi-language interviews are post-MVP.
