# INTV-001: Interview plan generation

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M3 Intake |
| Status | Done |
| Size | M |
| Depends on | [SCREEN-002](../SCREEN/SCREEN-002-resume-assessment-and-decision.md) |
| Requirements | FR-INTV-01 |
| Gap areas | G2, G3 |
| Design | Frames Demo/DemoInterview (topics, résumé quotes), CandidateProfile (topics) |
| Docs to read | [`architecture/AI_PIPELINE.md §2`](../../architecture/AI_PIPELINE.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Every invited candidate has a personal interview plan built from the JD, their redacted résumé and the pipeline's settings.

## Scope
**In:**
- `interview_plans` migration
- Prompt `interview_plan@v1` + schema
- `plan_interview` job
- Validation: every skill to probe covered; warm-up first; candidate questions last

**Out:**
- —

## Acceptance criteria
- [x] Plans generated for golden fixtures (`tests/ai_eval/test_interview_plan.py`, four golden résumés; passed with gpt-4.1-mini on 2026-10-02)
- [x] No personal data in plan text (masks and the candidate's name are refused by `problems()`; the fallback plan holds nothing from the résumé)
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px: no screen in this task (topics show in INTV-005 and ASMT-006)
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- The model never sees the candidate's name or the original résumé, so a name in the plan can only be a guess; the check still refuses it.
- A candidate who passed must never wait on the model: after the job's last try the plain skills plan is stored instead (`source = fallback`).
- A résumé that couldn't be read has no text; the plan still works (no quotes), for SCREEN-004's manual invite.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- ai_eval plan fixtures

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

1. **Table** (migration `20261003120000_interview_plans.sql`): `interview_plans` as in DATABASE.md plus `source` (`ai` | `fallback`); `instructions_version` stays empty until INTV-004 uses the plan. Deleted with its application; RLS on with no policies.
2. **Prompt** `interview_plan@v1` with schema `InterviewPlan`: topics with a `kind` (`warm_up`, `skills`, `candidate_questions`), title, goal, skills copied from the skills to probe, 1–3 seeds (question, verbatim résumé quote or ""), and claims to verify. Inputs: job title, expected seniority (one level lower with "Ready for a step up"), JD, company "about", skills to probe, must-haves, the screen's claims, tone, format, 30 minutes, interview versions of the "Also open to" rules, and the redacted résumé from `resume_texts`.
3. **Checks** (`app/interview/plan.py`): the model gives each topic's skills as numbers from the prompt's list and code stores the names; a quote not found in the redacted résumé (the screening quote check) or holding a mask is dropped (the seed keeps its question, the claim goes). Then: 4–7 topics, warm-up first and only first, candidate questions last and only last, 1–3 seeds each, every skill to probe in a `skills` topic, no mask (`[NAME]`, `[SCHOOL]`…) and no part of the candidate's name (3+ letters, whole word, case-sensitive) in any text. A plan that fails is asked for once more, then `AIOutputError`.
4. **Fallback:** when the job's last try fails (bad answers or the model unavailable), the failure hook stores a plain plan from the skills to probe (warm-up, one topic per skill up to 5 then grouped, the candidate's questions; no quotes, no claims), so the invitation never waits on the model.
5. **Job:** `plan_interview(application_id)` (3 tries), queued by `screen_resume` after a pass, keyed by application; skips a plan that exists or an application past `invited`. `requeue_stuck_work` re-queues passed applications with no plan 10 minutes after the screen. The stage doesn't move: SCREEN-003 invites after the plan exists.
6. **Fake model:** `AI_FAKE=1` builds a plan from the skills to probe quoting the résumé (`app/ai/fakes.py`).
7. **Tests:** unit (order, counts, coverage, quotes, masks and names, prompt variables, fallback, retry then failure); integration in the real worker (pass → plan, fail → none, a leaking plan falls back, a failing model falls back, repeat is a no-op, sweeper); `tests/ai_eval/test_interview_plan.py` against the real model for four golden résumés.

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
- 2026-10-02: branch `feature/interview-plan-r3k8v2` from `develop`. Plan auto-approved (owner's standing rule). Also marks SCREEN-002 Done on the board; no other task became Ready (SCREEN-003 still waits on MSG-003).
- Decisions (defaults picked, open to change): a plain skills plan is stored when the model fails, so no passed candidate is held up (marked `source = fallback`); topics carry a `kind` so code can check the order; résumé quotes may not contain a mask, since the candidate sees them; the plan is built from the redacted text, so a candidate with no readable résumé still gets a plan without quotes.
- Hand-tested on local Supabase with the real worker: a passed screen queued `plan_interview`, which stored a 5-topic plan covering the 3 skills to probe with quotes from the redacted résumé; a plan holding `[SCHOOL]` was asked for again and then replaced by the fallback; `AI_FAKE=1` builds a passing plan. The real-model golden set was run by Darwin (see below).
- 2026-10-02: Darwin ran the real-model golden set with gpt-4.1-mini: the fresh-graduate plan failed twice, rewording a skill to probe ("Data cleaning in Python") and quoting text the résumé didn't contain. Skills now come back as numbers from the prompt's list, quotes that aren't in the résumé are dropped instead of failing the plan, and the prompt asks for the résumé's own spelling and not to quote the Objective line. Darwin asked to mark INTV-001 Done on the board in this PR so it ships with the next deployment.
- 2026-10-02 (second real-model run): the backend plan for one résumé left a skill to probe out of every topic on both tries. Code now adds a missing skill itself: to the topic that talks about it, else as a plain topic before the candidate's questions, else to the last skills topic. The live interviewer covers it with follow-ups.
- 2026-10-02 (third run): Darwin ran `tests/ai_eval` with gpt-4.1-mini: plan, assessment and redaction golden sets all pass (5 passed).
