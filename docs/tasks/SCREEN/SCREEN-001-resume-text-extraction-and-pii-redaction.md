# SCREEN-001: Résumé text extraction and PII redaction

| Field | Value |
|---|---|
| Epic | SCREEN — Résumé screening |
| Milestone | M3 Intake |
| Status | Ready |
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
- [ ] Counterfactual fixtures: names, schools, years, addresses removed
- [ ] Unreadable PDFs never auto-rejected
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- ai_eval redaction fixtures

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
