# INTV-004: Realtime session service (server)

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M4 AI interview |
| Status | Done |
| Size | L |
| Depends on | [INTV-001](../INTV/INTV-001-interview-plan-generation.md), [INTV-002](../INTV/INTV-002-interview-link-page-and-states.md), [FND-013](../FND/FND-013-openai-integration-layer.md) |
| Requirements | FR-INTV-04 |
| Gap areas | G2, G3 |
| Design | — |
| Docs to read | [`architecture/MEDIA.md §2`](../../architecture/MEDIA.md), [`architecture/AI_PIPELINE.md §3`](../../architecture/AI_PIPELINE.md), [`decisions/ADR-007-openai-for-all-ai.md`](../../decisions/ADR-007-openai-for-all-ai.md), [`decisions/ADR-012-interview-format-rules.md`](../../decisions/ADR-012-interview-format-rules.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
The API starts, controls and ends OpenAI Realtime interview sessions with the right instructions and limits.

## Scope
**In:**
- Interviewer instruction builder (`app/ai/interviewer.py`, versioned)
- `POST …/session`: client secret, attempt row, time left
- Sideband connection: apply instructions, receive events/tool calls, wrap-up at 25 min, end at 30 min
- `POST …/heartbeat`, `POST …/complete`
- Resume summary for new attempts
- Cost logging (audio seconds)

**Out:**
- Browser UI (INTV-005)

## Acceptance criteria
- [x] Session can't exceed cap even if client misbehaves (the API opens every call, ADR-021; sideband hang-up, heartbeat check and every-minute watchdog)
- [x] Instructions contain fairness rules (and the sideband reverts browser changes to them)
- [x] Resume continues from the next topic
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Keep the provider behind an interface for testing
- The link page (INTV-002) reads `interviews.status`, `talk_seconds` and `drop_reason`: set `in_progress`/`abandoned` and `talk_seconds` as attempts run, and `drop_reason = technical_issue` after 3 failed connections so the page shows "We couldn't connect you". Look links up with `services/interview_links` (`hash_token` + `interview_link_of()`).

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Integration test with a fake Realtime server

## Implementation plan
_(Auto-approved per the owner's rule of 2026-09-29: plans are written here and built without a stop.)_

**Connection setup (ADR-021, proposed).** The browser sends its WebRTC offer to `POST …/session`; the API opens the OpenAI call with the server key (`POST /v1/realtime/calls`, the "unified interface") and returns the SDP answer. Audio still flows browser ↔ OpenAI. The API therefore always knows the call id, so it can attach the sideband and hang up at the cap whatever the browser does, and no OpenAI key reaches the browser. ADR-021 amends ADR-007's "client secret" line.

**Provider interface** — `app/ai/realtime.py`: `RealtimeProvider` (`create_call(sdp, session) → RealtimeCall(call_id, sdp)`, `attach(call_id) → Sideband` (send/recv JSON events), `hangup(call_id)`), `OpenAIRealtime` (SDK `realtime.calls`, sideband over `websockets` to `wss://…/v1/realtime?call_id=…`), `FakeRealtime` for `AI_FAKE=1` (canned answer, an idle sideband), `realtime_from_settings()`. Settings `OPENAI_REALTIME_MODEL`, `OPENAI_REALTIME_VOICE`, `OPENAI_CAPTION_MODEL` (live captions only). `OPENAI_PRICES` entries may add `audio_input` / `audio_output` per million tokens.

**Instructions** — `app/ai/interviewer.py` renders `app/ai/prompts/interviewer@v1.md` (`# System` = the instructions, `# User` = the opening cue the sideband sends so Ava speaks first): role & tone (never claims to be human), flow, fairness (protected attributes, nothing unrelated to the job, no follow-up on volunteered personal details), English only, time, tools, the plan's topics with seeds and claims, the JD and company "About" for the candidate's questions, and on a resume a summary of the topics covered and the topic to continue from. No candidate name. `TOOLS` (`set_topic`, `show_resume_quote`, `end_interview`), the session config (server VAD with 1 s silence, captions), and the wrap-up and goodbye messages live there too.

**Data** — migration `interview_attempts` (DATABASE.md columns + `connected_at`, `last_seen_at`, `topic_index`, `resume_from`, `wrap_up_sent_at`), RLS on, no public grants; model + `InterviewAttemptRepository`; `instructions_version` written on the plan.

**Service** — `app/services/interview_sessions.py`:
- `start()` (`POST /v1/candidate/interviews/{token}/session {sdp}`): the link must be open for this account (`404`/`409 interview_not_open`) with consent recorded (`409 interview_consent_required`); locks the interview; ends an open attempt (`disconnect`, or `error` if it never connected) and hangs it up; 3 never-connected attempts in 5 minutes → `drop_reason = technical_issue` and `409 interview_technical_issue`; no time left → completed (`time_cap`). Otherwise builds the instructions (resume from the topic after the furthest `set_topic`), creates the call, writes the attempt, `in_progress` + `started_at`, stage `interview_in_progress` (via `move_stage`), commits, queues `run_realtime_session(attempt_id)`. Returns `{attempt_id, sdp, time_left_seconds, wrap_up_in_seconds, heartbeat_seconds, topics[{index,title}], topic_index}`. Provider failure ends the attempt as `error` (`503 realtime_unavailable`; a rejected offer `422 realtime_offer_rejected`).
- `heartbeat()` (`POST …/heartbeat {attempt_id, connected}`): server-clock talk time on the attempt and interview, `connected_at` (clears a `technical_issue`), `last_seen_at`; past the cap it ends the attempt (`time_cap`) and hangs up. Returns `{status: active|wrap_up|ended, time_left_seconds, end_reason}`.
- `complete()` (`POST …/complete {attempt_id?}`): ends the open attempt (`candidate_ended`), interview `completed`, stage `scoring`, hangs up. Idempotent.
- `end_attempt()` shared by all paths: talk time, `abandoned` for `disconnect`/`error`, `completed` + stage `scoring` for `candidate_ended`/`wrap_up`/`time_cap`.

**Sideband** — `app/interview/sideband.py` `SessionController`, run by the `run_realtime_session` job (`app/jobs/realtime.py`, timeout cap + 5 min, retried to re-attach): applies the instructions and tools (`session.update`), sends the opening cue (`response.create`), then reacts to events and deadlines: tool calls (stores `topic_index`; `end_interview` ends the interview and hangs up once the goodbye has played or after 10 s), `session.updated` with other instructions or tools and unknown system messages are reverted (3 tampers end the attempt as `error`), `response.done` usage summed; at 25 min of total talk a wrap-up system message; 20 s before 30 min a goodbye; at 30 min hang up (`time_cap`). A closed socket ends the attempt as `disconnect`. One `ai_calls` row per run: purpose `interview_realtime`, tokens, `audio_seconds`, cost.

**Watchdog** — every-minute cron `end_overdue_attempts`: open attempts past their cap (+30 s) or without a heartbeat for 60 s are ended and hung up, so the cap holds even if the worker or the browser misbehaves. Worker `max_jobs` 10 → 50 (a live sideband mostly waits).

**Tests** — unit: instructions (fairness, tools, resume summary, no name), resume point, time limits. Integration: the routes with a fake provider (start, consent required, resume continues from the next topic, 3 failures → technical issue, heartbeat past the cap ends and hangs up, complete, wrong account 404), the controller against a fake Realtime WebSocket + HTTP server (session.update applied, set_topic stored, tamper reverted, wrap-up and cap with short limits, usage logged), the watchdog.

**Docs** — API.md, MEDIA.md §2, AI_PIPELINE.md §3, DATABASE.md, BACKEND.md jobs, DEPLOYMENT.md env, `.env.example`, `render.yaml`, ADR-021 (proposed), AGENTS.md status, BOARD.md.

**Needs the owner locally** — a real OpenAI Realtime run (no key in the cloud): see the PR.

## Log
- Branch `feature/intv-004-realtime-session-8r77u6` from `develop`; PR #44. Plan auto-approved per the owner's rule.
- Decision raised with the owner: the API opens each call with the browser's SDP offer instead of handing the browser a client secret (ADR-021, proposed, amends ADR-007), because with a client secret the API never learns a misbehaving browser's call id and can't enforce the cap. Built on that default while the owner decides.
- Deviations: `set_topic` takes a 1-based `number` (the model reads numbered topics); the API returns `topics[{number, title}]`. Talk time counts from the call's creation on the server's clock, so connection set-up (a second or two) counts. Chunk upload URLs are left to INTV-006. `interview_attempts` gained `connected_at`, `last_seen_at`, `seconds_allowed`, `resume_from`, `topic_index`, `wrap_up_sent_at`. Worker `max_jobs` 10 → 50.
- Not run against real OpenAI (no key in the cloud): the provider was tested against a fake Realtime server (WebSocket sideband, mocked REST). The owner runs one live session locally once INTV-005's UI exists, or with a small WebRTC script (see the PR).
