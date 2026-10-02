# SCREEN-002: Résumé assessment and decision

| Field | Value |
|---|---|
| Epic | SCREEN — Résumé screening |
| Milestone | M3 Intake |
| Status | Done |
| Size | L |
| Depends on | [SCREEN-001](../SCREEN/SCREEN-001-resume-text-extraction-and-pii-redaction.md), [PIPE-001](../PIPE/PIPE-001-pipeline-model-and-state-machine.md) |
| Requirements | FR-SCREEN-03, FR-SCREEN-04, FR-SCREEN-05, FR-SCREEN-06 |
| Gap areas | G2, G4 |
| Design | Frame CandidateProfile (Résumé tab data) |
| Docs to read | [`architecture/AI_PIPELINE.md §1`](../../architecture/AI_PIPELINE.md), [`decisions/ADR-013-resume-screening-rule.md`](../../decisions/ADR-013-resume-screening-rule.md), [`decisions/ADR-015-automated-decisions-human-review.md`](../../decisions/ADR-015-automated-decisions-human-review.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Each résumé gets an explainable fit score against the pipeline's criteria and a pass/fail decision, logged for audit.

## Scope
**In:**
- `resume_assessments` + `ai_decisions` migrations
- Prompt `resume_assessment@v1` + schema
- Score computed in code (40/20/25/15, redistribution)
- 'Also open to' rules
- `screen_resume` job end-to-end

**Out:**
- Emails and invites (SCREEN-003)

## Acceptance criteria
- [x] Pass rule = score ≥ bar and all must-haves met
- [x] Counterfactual pairs within ±3 points (same prompt by construction, unit-tested, and the real-model golden set passed with gpt-4.1-mini on 2026-10-02)
- [ ] p95 < 5 min on the QA environment (QA isn't deployed yet; every screen logs its time from applying, and `resume_assessments.duration_ms` keeps it)
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px: no screen in this task (the Résumé tab is ASMT-005)
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- ai_eval golden set

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

1. **Tables** (migration `20261003090000_resume_assessments.sql`): `resume_assessments` as in DATABASE.md plus `pass_bar` (the bar the decision used), deleted with its application; `ai_decisions`, append-only like `audit_log` (trigger + revoked update/delete), no FK to the application so the log outlives it, holding numbers and flags only, never résumé text. Both locked down with RLS.
2. **Prompt** `resume_assessment@v1` with schema `ResumeAssessment` (AI_PIPELINE.md §1 step 3): one result per must-have and nice-to-have in the pipeline's order with a verbatim `evidence_quote`, must-have `strength` 0–3 and `degree_requirement`, experience and skill depth scores 0–100, impact, claims to verify, timeline and career snapshot. Inputs: job title, expected seniority, JD, numbered must-haves and nice-to-haves, the "Also open to" rules that apply, and the redacted text from `resume_texts`. Temperature 0.
3. **Answer checks** (`app/screening/assess.py`): an answer is used only when it covers every criterion (matched by text, or by position when the count matches) and every met must-have and found nice-to-have quotes the résumé word for word (case, spacing, curly quotes and dash styles ignored). Otherwise it is asked once more, then `AIOutputError`, so the job ends with `resume_status = error` for a person.
4. **Score in code** (ADR-013): must = 100 × met/total, nice = 100 × found/total, plus experience and skill depth, weighted 40/20/25/15; a part with no criteria is dropped and the rest scaled proportionally; total rounded half up. Pass = score ≥ pass bar and every must-have met.
5. **"Also open to"** (step 5): every selected rule's text goes into the prompt; Ready for a step up lowers the expected seniority one level before it reaches the prompt; Fresh graduates sets an experience floor of 50 for entry and mid roles (for everyone, so nothing has to guess who is a graduate); No degree required counts a degree-only must-have as met.
6. **Job:** `screen_resume` runs `prepare_resume()` then `assess_resume()`, each done once and skipped on a repeat, so a retry resumes where it stopped. `assess_resume()` writes the assessment, its `ai_decisions` row and `resume_status = done` in one transaction. The stage stays `processing_resume`; SCREEN-003 moves it (invite, or `resume_not_match` and the rejection email), since that task owns both moves and their emails.
7. **Fake model:** `AI_FAKE=1` answers `resume_assessment@v1` from a builder (`app/ai/fakes.py`) that mirrors the pipeline's criteria and quotes the résumé, so local runs and e2e pass the screen for any pipeline.
8. **Tests:** unit (design example 88, redistribution, pass rule edges, each open-to rule, quote and coverage checks, retry then failure, fake answer, counterfactual pairs reach the model as the same prompt); integration in the real worker (pass logged, missing must-have fails whatever the score, invented evidence ends in error, repeat run is a no-op, `ai_decisions` rejects update and delete, sweeper); `tests/ai_eval/test_resume_assessment.py` golden set (two counterfactual pairs within ±3, one clear mismatch) against the real model.

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
- 2026-10-02: branch `feature/screen-002-ksc2ju` from `develop`. Plan auto-approved (owner's standing rule). Also marks SCREEN-001 Done on the board.
- Decisions (defaults picked, open to change): the stage isn't moved here, so SCREEN-003 makes both moves with their emails and a screened application waits as `processing_resume` + `resume_status = done`; must-have `strength` is 0–3 (0 = not met) instead of 1–3; the fresh-graduate experience floor is 50 and applies to every applicant for entry and mid roles; `resume_assessments.pass_bar` added so the profile shows the bar the decision used; `duration_ms` is from applying to the decision (what FR-SCREEN-06 and the Résumé tab's "Time to screen" measure). An answer whose quotes aren't in the résumé is never used, even if it would pass the candidate.
- Hand-tested on local Supabase with the real worker and `AI_FAKE=1`: a submitted PDF was redacted, assessed (89, pass: 3 of 3 must-haves, no nice-to-haves so their weight was redistributed), logged to `ai_decisions` with numbers only, and `ai_calls` recorded both prompts. The real-model golden set wasn't run (no OpenAI key in this session); run it with `AI_EVAL=1` before relying on scores in development.
- 2026-10-02: Darwin ran the golden set with gpt-4.1-mini. Two findings, both fixed: (1) the model left school names in the fresh-graduate pair's Education section, so redaction rules are now `rules@v2` and mask school names found there (a run of capitalised words with an institution word such as University, College or Institute) everywhere in the text; (2) the quote check rejected two nice-to-have quotes, so it now compares words in order with case, punctuation and line breaks ignored, and accepts a quote shortened with "..." when every part is found in order. The eval now prints any quotes it couldn't find.
- 2026-10-02 (second golden-set run): the model joins evidence from several sections into one quote ("BS Statistics … \nSkills\n… statistics"), so a quote is now split at line breaks and "..." and every piece must be in the résumé; and it masked "Engr." with the referee's name in one résumé of a pair but not the other, so titles directly before `[NAME]` (Engr., Dr., Mr., Ms. …) are now always removed.
- 2026-10-02 (third run): Darwin ran `tests/ai_eval` with gpt-4.1-mini: redaction and assessment golden sets both pass (4 passed).
- 2026-10-02: merged as PR #37.
