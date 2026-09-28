# AI pipeline

All AI runs on OpenAI (ADR-007) through `apps/api/app/ai/`. This document defines what each AI step receives, what it must return, and the fairness guardrails. Prompts live in `app/ai/prompts/<name>@vN.md`; output schemas in `app/ai/schemas/`. Bump the version on any prompt change and re-run the evaluation set.

## 0. Principles
1. **Job-related evidence only.** Inputs to scoring never contain name, photo, contact details, address, age/date of birth, gender, graduation years or school names (G2).
2. **Evidence or it didn't happen.** Every score must cite verbatim quotes (résumé text or transcript with timestamps). Scores without evidence fail schema validation.
3. **Structured outputs.** Every text-model call uses a JSON schema; invalid output → one retry → job error (never silently accepted).
4. **Deterministic settings.** Low temperature for scoring; seeds where supported; record model + prompt version.
5. **Humans decide.** AI outputs are recommendations stored with `ai_decisions`; review routes exist for every automated outcome (ADR-015).

## 1. Résumé screening (`screen_resume`)
**Steps**
1. **Extract** text with `pdfplumber` (layout-aware). If < 200 characters of text → `resume_status = unreadable`; stop (TA sees "Couldn't read résumé").
2. **Redact** with a two-pass approach: (a) deterministic rules (emails, phones, URLs, addresses, dates of birth, years next to education entries); (b) a text-model call that returns spans to mask for name, gender markers, age, school names, photo captions. The redacted text is what every later step sees. Keep the original only for the TA's PDF view.
3. **Assess** (text model, schema `ResumeAssessment`): inputs = redacted text, JD, must-haves, nice-to-haves, seniority, "Also open to". Output:
   - `must_haves[]`: `{criterion, met: bool, evidence_quote, strength 1–3, note}` — related/transferable experience counts as met.
   - `nice_to_haves[]`: `{criterion, found, where}`.
   - `experience`: `{relevant_years, required_hint, score 0–100, note}`.
   - `skill_depth`: `{score 0–100, note}`.
   - `impact[]`: `{value, statement}`; `claims[]`: `{requirement, type, found, strength}`; `timeline[]`, `career_snapshot`.
4. **Compute** in code (not by the model): `score = 0.40·must + 0.20·nice + 0.25·experience + 0.15·skill_depth`, where `must = 100 × met/total`, `nice = 100 × found/total` (weights redistributed if no nice-to-haves). Pass = `score ≥ resume_pass_bar` **and** every must-have met.
5. **"Also open to" rules** (added to the prompt and to step 4):
   - Fresh graduates: internships, school and personal projects count as experience; experience score floor applies for entry/mid roles.
   - Career changers: transferable skills can satisfy must-haves.
   - Returning to work: gaps are never mentioned or penalised.
   - No degree required: degree requirements in the JD are ignored.
   - Ready for a step up: seniority expectation drops one level.
   - Relocating / remote-first: location is never a gap.
6. Write `resume_assessments`, `ai_decisions`, then continue per WORKFLOW.md.

## 2. Interview plan (`plan_interview`)
Inputs: JD, redacted résumé assessment (quotes, claims to verify), skills to probe, seniority, tone, company "about". Output schema `InterviewPlan`:
- 4–7 `topics` in order (warm-up first, candidate's questions last), each with `goal`, `skills[]`, 1–3 `seeds` (`question`, `resume_quote` for the "From your résumé" line).
- Every skill to probe appears in at least one topic.
- `claims_to_verify[]` from the résumé.
No fixed question count is imposed on the live interviewer; seeds are starting points.

## 3. Live interviewer (Realtime session instructions)
Built by `app/ai/interviewer.py` from the plan + pipeline settings. Instruction blocks:
- **Role & tone:** "You are the AI interviewer for {Company}. Tone: {warm|professional|direct}. Seniority: {…}." Never claim to be human; if asked, say you're an AI interviewer and a person on the hiring team makes decisions.
- **Flow:** greet, confirm readiness, follow topics in order, ask one question at a time, follow up on vague answers (depth by seniority/tone), move on after ~2 follow-ups, answer candidate questions **only** from the JD and company profile (otherwise: "The hiring team can share more in the next round"), keep answers short.
- **Fairness:** never ask about age, family, health, religion, nationality/immigration status, ethnicity, sexual orientation, pregnancy, disability, salary history, or anything unrelated to the job; if the candidate volunteers such information, don't follow up on it.
- **Time:** the server sends a wrap-up instruction at 25 min and ends at 30 min; the interviewer thanks the candidate and explains next steps.
- **Tools** (function calls the model can make, handled via the sideband/data channel): `set_topic(index)` (drives the topic list UI), `show_resume_quote(text)`, `end_interview(reason)`.
- **Resume:** on a new attempt, the instructions include a short summary of topics covered so far and continue from the next topic.

## 4. Scoring (`score_interview`)
Inputs: authoritative transcript (with timestamps, speakers), plan, JD, redacted résumé assessment, rubric weights. Schema `InterviewAssessment`:
- For each criterion (`technical`, `communication`, `culture`): `score 0–100`, `signals[]` (3–5 sub-skills with scores — e.g. technical: system design, databases at scale; communication: structure and clarity, answers the question asked, concise; culture: ownership, collaboration, curiosity), `evidence[]` (2–4 quotes with `start_ms`, or résumé refs), `held_back` (one sentence).
- `topics[]` with scores; `summary` with numbered references; `strengths[]` and `probes[]` (each with a reason); `claims_checked[]` (Confirmed / Partly confirmed / Not covered / Probe next round).
- Code computes: overall = Σ(score × weight) rounded; `passed = overall ≥ pass_mark`; fit per ADR-011; `answer_stats` (avg answer length, response delay, follow-ups, candidate questions, talk time) from transcript timings, not from the model.
- **Culture alignment** is defined as job-related working behaviours (ownership, collaboration, communication with the team, learning) — never "fit" with a demographic or personality type. The prompt states this explicitly.
- Pipeline aggregates (rank, average, distribution, comparisons) are computed in SQL.

## 5. Integrity analysis (`check_integrity`, ADR-016)
- Face checks: local model in the worker on frames sampled every 2 s (video only) — see `MEDIA.md`.
- Second voice: diarised transcription; segments attributed to a third speaker → `second_voice` flag with times.
- Read-aloud and timing: features computed in code (response delay distribution, speech-rate uniformity, pause-before-answer vs answer fluency) + a text-model judgement over flagged windows returning `{flag: bool, confidence, rationale, start_ms, end_ms}`.
- Thresholds are config; flags carry confidence; nothing auto-rejects.

## 6. Ava (TA assistant)
- Tool-using agent (Responses API with function calling). Tools are thin wrappers over repositories and **require the caller's `RequestContext`**: `list_candidates(filters)`, `get_assessment(application_id)`, `search_transcripts(query)`, `get_resume_screen_stats()`, `get_flags()`, `get_pipeline_stats()`, `find_past_candidates(jd_or_skills)` (workspace scope only).
- **Protected-attribute guard:** a pre-check classifies the question; if it asks to compare/filter/rank on protected or personal attributes, Ava returns the refusal message (FR-AVA-03) without calling tools. The system prompt repeats the rule.
- Output schema: `{paras[], table?, bullets[], note?, sources[{label, kind, ref}]}`; every factual claim must map to a source; answers stream to the UI (SSE).
- Ava never writes; it has no mutating tools.

## 7. Evaluation and monitoring
- `tests/ai_eval/`: golden résumés (incl. counterfactual pairs that differ only in name/gender/age/school), JDs and transcripts with expected ranges. CI job (manual trigger + before prompt version bumps) reports score deltas and parity across counterfactual pairs (must be within ±3 points).
- Production: `ai_calls` gives cost and latency per step; alert when p95 screening > 5 min or scoring > 20 min.
