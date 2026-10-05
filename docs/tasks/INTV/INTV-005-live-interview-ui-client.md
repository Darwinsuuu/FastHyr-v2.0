# INTV-005: Live interview UI (client)

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M4 AI interview |
| Status | Done |
| Size | L |
| Depends on | [INTV-003](../INTV/INTV-003-device-check-and-consent.md), [INTV-004](../INTV/INTV-004-realtime-session-service-server.md) |
| Requirements | FR-INTV-04, FR-INTV-09 |
| Gap areas | G3 |
| Design | Frame DemoInterview |
| Docs to read | [`architecture/MEDIA.md §2`](../../architecture/MEDIA.md), [`architecture/FRONTEND.md §4`](../../architecture/FRONTEND.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Candidates hold a natural voice/video conversation with the AI interviewer in a calm, accessible interface.

## Scope
**In:**
- `lib/interview/realtime.ts` + `session.ts` state machine
- Stage UI: status, current line, 'From your résumé', captions/transcript, topics, mute, end (with confirm), time remaining, self-view
- Reconnect and error screens
- Keyboard and screen-reader support

**Out:**
- Recording (INTV-006)

## Acceptance criteria
- [ ] First AI utterance < 1.5 s after connect (p75) — measured in the browser as `interview:first-utterance`; needs live runs against OpenAI (owner, locally)
- [x] Captions for every AI question
- [x] Mute pauses mic and shows status
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Playwright with fake media devices

## Implementation plan
**Flow.** The link page's client part (`InterviewFlow`) owns the step: link card → device check → live interview. The device check's Start records consent (as before) and hands over the chosen camera and microphone; the holding "You're all set" goes. The live view takes the whole page, header included (timer and "Live · {role}"). When the session ends, the page refreshes and shows the link's new state (completed, resume, or "We couldn't connect you"); the S-02 end screen with feedback stays with INTV-009.

**`lib/interview/realtime.ts`** — the WebRTC side (ADR-021): opens the mic (and camera for video interviews) with the chosen devices, builds an `RTCPeerConnection` with the mic track and the `oai-events` data channel, posts the offer through a `startSession(sdp)` callback (`POST …/session`), applies the answer, plays the interviewer's audio, and reports connection state and parsed data-channel events. Mute sets the mic track's `enabled`. It never answers tool calls or sends session events. A scripted fake connection (`fake-realtime.ts`) plays a short conversation with the same event shapes when the API answers with the `AI_FAKE` SDP and the app isn't production, so the UI runs locally and in Playwright with no OpenAI key.

**`lib/interview/session.ts`** — a pure reducer (`connecting → live → reconnecting → ending → ended`, or `failed`) that turns events into what the stage shows: interviewer status (speaking, listening, thinking, paused while muted), the current AI line, captions in order (AI from response transcripts, candidate from input transcription), the topic from `set_topic` (1-based), the résumé quote from `show_resume_quote`, `end_interview` → ending, the countdown (local tick, corrected by each heartbeat), wrap-up. A `useInterviewSession` hook drives it: first heartbeat the moment the peer connection is up, then every `heartbeat_seconds`; `ended` from a heartbeat or `/complete` closes everything; a failed or long-disconnected connection (or one that never connects in 15 s) reconnects with a new `/session` call (up to 3 times, then the error screen with Try again); `409 interview_technical_issue` / `interview_not_open` refresh the page; the time from connect to the first AI audio is measured (`performance.measure`).

**Stage UI** (`components/interview/live-interview.tsx`, frame DemoInterview): status, current line and "From your résumé", live captions (`role="log"`, polite), Mute/Unmute (`aria-pressed`, status "Paused — your mic is off"), End interview with a confirm dialog, time remaining (`role="timer"`, warning colour under 2 minutes, a screen-reader announcement at 5 and 1 minutes), self-view (mirrored camera, or "mic on" for voice only), "What we'll talk about" with progress, "Good to know". Reconnecting and error screens. Mobile first: one column with the controls pinned at the bottom and a small self-view; the side column from `lg`. Leaving the page asks first while live.

**Mute and the model.** MEDIA.md says mute also tells the model. The browser can't send the model a message (the sideband treats that as tampering), and with server VAD a silent mic never ends a turn, so the interviewer simply waits. Mute is client-only; MEDIA.md is updated to say so.

**Tests** — vitest for the reducer (caption order, tool calls, mute status, countdown and heartbeat correction, reconnect and ending) and event parsing; Playwright with Chromium's fake media devices on a dev-only preview page that runs the live UI against the fake connection (captions, topics, mute, end with confirm). The real path (session, heartbeat, complete) is hand-tested against the local API with `AI_FAKE=1`.

**Docs** — MEDIA.md §2, FRONTEND.md §4, SCREEN_SPECS.md S-01 note, AGENTS.md status, BOARD.md.

**Needs the owner locally** — one live run against OpenAI with `OPENAI_REALTIME_MODEL` and `OPENAI_CAPTION_MODEL` set on the API and worker (see the PR).

## Log
- Branch `feature/intv-005-interview-screen-7hm2d8` from `develop`.
- Deviations: mute is client-only (see the plan; MEDIA.md updated). The device check now hands the chosen camera and microphone to the live interview, and its holding "You're all set" is gone. When a session ends the link page reloads and shows the link's state ("You've finished this interview" until INTV-009's end screen). Talk time keeps running on the server between a reload and the next "Continue my interview", as INTV-004 counts it. The kit's `ConfirmDialog` now stays open quietly when `onConfirm` rejects (it used to leave an unhandled rejection).
- Hand-tested against the local API with `AI_FAKE=1` and Chromium's fake devices: apply → screened → invited (Mailpit link) → device check → live → End interview (interview `completed`, stage `scoring`, attempt `candidate_ended`); and reload mid-interview → "Welcome back" → Continue (first attempt `disconnect`, second `candidate_ended`). The scripted stand-in plays the conversation, so the stage was checked at 360, 768, 1024 and 1440 px, light and dark.
- Not run against real OpenAI (no key in the cloud): the owner checks one live session locally with `OPENAI_REALTIME_MODEL` and `OPENAI_CAPTION_MODEL` set on the API and worker (see the PR).
