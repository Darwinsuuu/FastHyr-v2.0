# SCREEN-001: Résumé text extraction and PII redaction

| Field | Value |
|---|---|
| Epic | SCREEN — Résumé screening |
| Milestone | M3 Intake |
| Status | In review |
| Size | M |
| Depends on | [FND-011](../FND/FND-011-storage-service-and-pdf-handling.md), [FND-013](../FND/FND-013-openai-integration-layer.md) |
| Requirements | FR-SCREEN-01, FR-SCREEN-02 |
| Gap areas | G2 |
| Design | — |
| Docs to read | [`architecture/AI_PIPELINE.md §1 steps 1–2`](../../architecture/AI_PIPELINE.md), [`compliance/BIAS_FAIRNESS.md`](../../compliance/BIAS_FAIRNESS.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Résumé text is extracted and stripped of personal details before any AI scoring.

## Scope
**In:**
- pdfplumber extraction with layout handling
- Rule-based + model-assisted redaction producing redacted text
- Unreadable detection (`resume_status = unreadable`)

**Out:**
- —

## Acceptance criteria
- [x] Counterfactual fixtures: names, schools, years, addresses removed
- [x] Unreadable PDFs never auto-rejected
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- ai_eval redaction fixtures

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

1. **Extraction** (`app/screening/extract.py`, pdfplumber): each page is checked for a two-column layout (a vertical gutter in the middle half of the page that no body word crosses, where the right side's lines don't share baselines with the left side, so "Title …… 2019 – 2021" rows stay one line). Column pages are read header, left column, right column; other pages read normally. Text is normalised (NFKC, `(cid:N)` glyph junk removed, hyphenated line breaks joined, spaces and blank lines collapsed). Fewer than 200 non-space characters, or a PDF pdfplumber can't open, is **unreadable**.
2. **Redaction** (`app/screening/redact.py`), two passes per AI_PIPELINE.md §1:
   - Rules: emails, links (URLs and bare profile domains), phone numbers (not year ranges or dates), labelled personal lines (address, date of birth, age, gender or sex, civil status, nationality, religion, height and weight, place of birth), "N years old", graduation phrases ("Class of 2015"), every year inside an Education section, street addresses, and the candidate's own name from the application.
   - Model: prompt `resume_redaction@v1` with schema `ResumeRedaction` (`spans[]: {text, kind}`; kinds name, gender, age, school, address, personal, photo) reads the rule-redacted text; every whole-word occurrence of each returned span is masked. Masks are readable labels (`[NAME]`, `[SCHOOL]`, `[YEAR]`…) so later steps still see the structure.
3. **Storage:** new table `resume_texts` (application_id PK, workspace_id, `redacted_text`, characters, pages, column pages, masked counts per kind, redaction version, created_at), locked down with RLS like every table and deleted with its application. Only the redacted text is stored; the original stays the PDF. This replaces `resume_assessments.redacted_text` in DATABASE.md, so SCREEN-002 reads the text from here.
4. **Job:** `screen_resume` calls `services/screening.prepare_resume()`: skip if not pending or already redacted (SCREEN-002 continues from there); download the PDF; extract in a thread; unreadable → `resume_status = unreadable` and the stage stays `processing_resume` (never rejected); otherwise redact and save. An invalid model answer (after the client's one retry) or a missing PDF fails permanently; after the last try the failure hook sets `resume_status = error`. The worker gets an AI client in `ctx["ai"]` (`AI_FAKE=1` uses the new fixture).
5. **Sweeper:** `requeue_stuck_work` also re-queues applications still `pending` 10 minutes after applying (keyed by application, so no duplicates).
6. **Tests:** unit tests for extraction (generated PDFs: single column, two columns, right-aligned dates, unreadable) and redaction (counterfactual résumé pairs that differ only in name, school, years and address must redact to the same text, with the fake model answering the spans a correct model finds); an integration test running the job in the worker (redacted, unreadable, error, sweeper); `tests/ai_eval/test_resume_redaction.py` runs the same counterfactual cases through the real model.

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
- 2026-10-02: branch `feature/screen-001-t27e05` from `develop`.
- Decisions: the redacted text lives in its own table, `resume_texts`, instead of `resume_assessments.redacted_text` (DATABASE.md left the choice open between a column and a Storage path); SCREEN-002 reads it from there, so the assessment row is only written once it has a score. No unredacted text is stored. Masks are readable labels so later prompts still see the résumé's shape. Until SCREEN-002, a redacted application stays `resume_status = pending` and the sweeper re-queues it every 10 minutes as a cheap no-op.
- Layout handling was hand-tested on PDFs printed by Chromium from HTML résumés: a two-column résumé with a 30% sidebar (read sidebar then main column; before the fix the sidebar's address line and the main column's dates interleaved) and a one-column résumé with right-aligned dates (rows kept whole). Two bugs found that way and fixed with tests: "(2016 - 2020)" was masked as a phone number, and "barangay health centres" in a job entry was masked as an address.
- Counterfactual fixtures: `tests/ai_eval/cases/resume_redaction@v1/` (two pairs differing only in name, gender, school, graduation year, birth date, address and contact details). The unit test runs them with the spans a correct model returns and requires identical redacted text per pair; `tests/ai_eval/test_resume_redaction.py` runs them through the real model (`AI_EVAL=1`, needs an OpenAI key; not run in this PR's session, which has none).
