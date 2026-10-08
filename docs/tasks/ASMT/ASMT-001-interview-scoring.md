# ASMT-001: Interview scoring

| Field | Value |
|---|---|
| Epic | ASMT — Assessment & review |
| Milestone | M5 Review |
| Status | Done |
| Size | L |
| Depends on | [INTV-008](../INTV/INTV-008-authoritative-transcription.md), [FND-013](../FND/FND-013-openai-integration-layer.md) |
| Requirements | FR-ASMT-02, FR-ASMT-03, FR-ASMT-04, FR-ASMT-05, FR-ASMT-09 |
| Gap areas | G2, G4 |
| Design | Frame CandidateProfile (overview data) |
| Docs to read | [`architecture/AI_PIPELINE.md §4`](../../architecture/AI_PIPELINE.md), [`decisions/ADR-011-numeric-explainable-scores.md`](../../decisions/ADR-011-numeric-explainable-scores.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Each finished interview gets an explainable assessment and the candidate moves to Ready for review or Didn't pass.

## Scope
**In:**
- `assessments` migration
- Prompt `interview_assessment@v1` + schema requiring evidence
- Overall/fit/answer stats computed in code; rubric snapshot
- `score_interview` job, stage update, `ai_decisions`
- Schedule `reject_interview` (3 business days) if enabled

**Out:**
- —

## Acceptance criteria
- [x] Scores without evidence rejected
- [ ] Transcript counterfactuals within ±5 on communication
- [ ] p95 < 20 min
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md)) — no UI in this task
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- ai_eval scoring set

## Implementation plan
_(Auto-approved per the owner's rule: plans are written here and built without a sign-off.)_

1. **Migration `assessments`** (expand-only): `assessments` as DATABASE.md (one per interview, unique `interview_id`; deleted with the application), plus `fit` (`strong_fit|good_fit|null`, ADR-011). `interviews.assessment_status` (`none|ready|failed`) so the sweeper knows what still needs scoring and a failed score waits for a person instead of looping. RLS on, no grants to public keys.
2. **Schema + prompt `interview_assessment@v1`** (`app/ai/schemas/interview_assessment.py`, `app/ai/prompts/interview_assessment@v1.md`). The model gets the job, the plan topics (numbered), the résumé claims to check (numbered), the redacted résumé, and the transcript as numbered turns (`#12 [03:21] Candidate: …`, consecutive lines of one speaker joined; `other` voices left out; the candidate's name and contact details masked with the résumé redaction rules). Per criterion: score, 3–5 signals, 2–4 evidence items (`interview` with a turn number and a verbatim quote, or `resume` with a verbatim quote) and what held it back; topic scores by number; summary with `[n]` references; strengths and probes with reasons; one status per claim (`confirmed|partly_confirmed|not_covered|probe_next_round`) with the turn; and the turn numbers of new questions, follow-ups and the candidate's own questions. Culture alignment is defined in the prompt as job-related working behaviours only; accent, grammar, filler words and non-native phrasing never lower communication.
3. **Checking the answer** (`app/interview/assessment.py`, pure): evidence must quote its turn (a candidate turn) or the résumé word for word (`quoted()` from screening); unverifiable items are dropped; a criterion left with fewer than 2 items or no interview quote, a covered topic without a score, or a summary reference that doesn't check out makes the answer unusable: asked once more, then `AIOutputError` (FR-ASMT-03, "scores without evidence rejected").
4. **Computed in code:** points = score × weight, overall = Σ rounded half up, `passed = overall ≥ pass_mark`, fit per ADR-011 (strong = passed, ≥ 80 and every résumé must-have met), rubric snapshot (weights + pass mark), topics (title from the plan, start = first line in it, questions/follow-ups counted from the turn labels), `answer_stats` from transcript timings: average answer length, average response delay, questions, follow-ups, candidate questions, talk-time share.
5. **Job `score_interview(workspace_id, interview_id)`** (`app/jobs/scoring.py`, service `services/scoring.py`): queued by `transcribe_interview` when the transcript is ready, and by `requeue_stuck_work` for ready transcripts still unscored after 10 minutes. Skips unless the interview is live, completed, transcribed and unscored. One transaction writes the assessment, an `ai_decisions` row (`interview_score`, pass/fail, numbers only), `assessment_status = ready`, and, if the application is still in `scoring`, moves it to `ready_for_review` or `did_not_pass` via `move_stage()`. A fail schedules `reject_interview` 3 business days after the interview completed with a `review_links` row (`decision_type = interview`), when the pipeline's "Email candidates after their interview" toggle (`email_post_interview`) is on. 3 tries; the failure hook sets `assessment_status = failed` (stage stays `scoring`). A transcript with no candidate speech is never scored (failed, for a person to look at).
6. **AI_FAKE** builder in `app/ai/fakes.py` that quotes the transcript turns it is given, so local runs and e2e reach Ready for review.
7. **Docs:** AI_PIPELINE.md §4 as built, DATABASE.md, NOTIFICATIONS.md (which toggle sends `reject_interview`), BACKEND.md jobs list, AGENTS.md status, BOARD.md (ASMT-001 Done; DASH-003 Ready).

**Not here:** the `interview_received` email (INTV-009), pipeline aggregates and the profile UI (ASMT-004), integrity flags (ASMT-002). There is no UI, so the responsive criterion doesn't apply.

**Tests:** unit tests for evidence checks, the computed numbers, fit and answer stats; integration tests for the job through the worker (pass → `ready_for_review`; fail → `did_not_pass` with the rejection and review link; toggle off; invented evidence → failed; repeat is a no-op; sweeper requeue); `tests/ai_eval` scoring cases with transcript counterfactual pairs (communication within ±5), run by the owner with a key.

## Log
- 2026-10-08: branch `feature/asmt-001-interview-scoring-nuloyl`. Plan auto-approved (owner's rule).
- Built as planned. Tests: `tests/unit/test_interview_assessment.py` (turns, masking, evidence checks, weighted overall and rounding, pass mark and fit, topics, claims, answer patterns, the retry) and `tests/integration/test_scoring.py` (pass, fail with `reject_interview` and its review link, toggle off, invented evidence, no candidate speech, a candidate who left `scoring`, the sweeper); `test_transcripts.py` now checks a ready transcript gets scored.
- Not checked here (no OpenAI key in the cloud container): `tests/ai_eval/test_interview_assessment.py` (strong and weak transcripts; counterfactual pairs for personal details and for native vs non-native phrasing, communication within ±5). The owner runs it with a key. p95 < 20 min: the job starts as soon as the transcript is ready and logs minutes since the interview; confirm on dev with a real interview.
- Decisions taken without asking: `reject_interview` follows the pipeline's "Email candidates after their interview" toggle (`email_post_interview`, shown as "Interview results" in the wizard), since there is no separate toggle; added `assessments.fit` and `interviews.assessment_status` (`none|ready|failed`); a failed or empty-transcript scoring leaves the application in `scoring` for a person, never rejected; other voices are left out of scoring.
