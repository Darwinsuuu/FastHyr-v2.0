# INTV-003: Device check and consent

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M4 AI interview |
| Status | Done |
| Size | M |
| Depends on | [INTV-002](../INTV/INTV-002-interview-link-page-and-states.md), [COMP-002](../COMP/COMP-002-notices-and-consent-versioning.md) |
| Requirements | FR-INTV-03 |
| Gap areas | G1, G7 |
| Design | Frame DemoDeviceCheck + S-01 consent |
| Docs to read | [`architecture/MEDIA.md §1`](../../architecture/MEDIA.md), [`compliance/PRIVACY.md §3`](../../compliance/PRIVACY.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Candidates confirm camera and microphone work and give informed consent before starting.

## Scope
**In:**
- `lib/interview/devices.ts` (permissions, pickers, level meter, face-in-frame, wave detection with fallback)
- Device check UI (video vs voice-only)
- Permission-denied help per browser
- `POST …/consent` storing consent + biometric consent versions

**Out:**
- —

## Acceptance criteria
- [x] Start disabled until checks + required consents
- [x] Works on mobile Safari/Chrome
- [x] No media leaves the browser during the check
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- INTV-002 left a holding step in `components/interview/interview-link-card.tsx` (`HoldingStep`): "Check my camera and mic", "Continue my interview" and "Try again" open it. Replace it with the device check.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Manual matrix across browsers
- Done: API integration tests in `tests/integration/test_interview_links.py` (consent stored with versions, biometric only for video + integrity, notice errors, other accounts and closed links); unit tests in `lib/interview/devices.test.ts` (error classification, browser help, device pickers, meter and read-aloud, wave, face judgement, readiness).

## Implementation plan
Plan auto-approved (project rule: no plan approval stops).

**API**
1. `InterviewLink` gains `face_check` (video format and the pipeline's "Flag possible impersonation" on): the page shows the biometric checkbox only then (S-01, ADR-016). `InterviewLinkRow` reads `pipelines.integrity_enabled`.
2. `POST /v1/candidate/interviews/{token}/consent` (`CandidateContextDep`) with `{consent_notice_id, biometric_notice_id?}` in `services/interview_links.record_consent()`: unknown token or another account is `404 interview_not_found` (nothing learned about the link); a link that can't start (expired, closed, completed) is `409 interview_not_open`; both notices go through `services/consents.accept()` (`409 notice_outdated`, `422 notice_unknown`); a face-check interview without the biometric consent is `422 biometric_consent_required`, and a biometric id sent for an interview without the check is ignored. Stores `consent_version`, `consent_at` and `biometric_consent_version` on `interviews`; agreeing again (resume, another try) replaces them with the latest agreement. No schema change: the columns came with SCREEN-003.

**Web**
3. `lib/interview/devices.ts`: getUserMedia with constraints from the remembered devices (`localStorage`, try/catch), error classification (`denied`, `not_found`, `in_use`, `unsupported`), browser detection and per-browser fix steps, `enumerateDevices` pickers, the level meter (`AnalyserNode` RMS), the read-aloud check (≥ 2 s of speech-level audio while reading), motion detection in the top-right of the mirrored preview (frame differencing on a small canvas) with the "I can see myself" fallback after 5 s, and face-in-frame from MediaPipe Face Detection (one face, centred, enough light). Pure parts (classification, help, meter, speech and motion detectors, face judgement, readiness) are separate functions for unit tests.
4. MediaPipe runs on the device: `@mediapipe/tasks-vision` is imported only on the device check; its WASM is copied from `node_modules` into `public/mediapipe/` by `scripts/copy-mediapipe.mjs` (run by `dev` and `build`, git-ignored) and the BlazeFace short-range model is committed in `public/mediapipe/`, so nothing is fetched from a third party and no frame leaves the browser. If it can't load, the camera check falls back to wave/"I can see myself" alone.
5. `components/interview/device-check.tsx` replaces `HoldingStep`: an explanation before the browser prompt ("Allow camera and microphone", which also starts the `AudioContext` inside the tap for iOS Safari), then the DemoDeviceCheck layout without the demo toggle: camera card (video only) and microphone card, stacked on phones and side by side from `lg`; pickers under each preview; permission-denied help for the detected browser; the consent checkboxes from `/v1/public/notices` with `ConsentCheckbox variant="plain"` (biometric only when `face_check`); "Start interview" disabled until the checks pass and the required boxes are ticked. Start records the consent, stops the camera and mic, and shows a holding message until INTV-005 builds the live interview.
6. Copy in `messages/en.json`; docs: API.md, MEDIA.md §1 notes, SCREEN_SPECS S-01, AGENTS.md status, BOARD.md (INTV-003 Done; INTV-005 waits on INTV-004).

**Defaults picked**
- The camera check passes on a wave with a face in frame, or by "I can see myself" after 5 s with the camera on, so no one is blocked by detection (integrity checks never reject anyone on their own).
- The mic check passes after 2 s of speech-level audio; after 20 s without it the card says how to fix it and lets the candidate try again.

**Tests**
- API: consent stored with versions; biometric required only for video + integrity; outdated/unknown notices; another account, signed out, closed link.
- Web unit: error classification and browser help, speech and motion detectors, face judgement, readiness.
- By hand: Chromium with fake camera and mic at 360, 768, 1024, 1440 px; denied permission; voice-only.

## Log
- Branch `feature/intv-003-device-check-epkz2k`. Plan auto-approved per the project rule.
- Built as planned. Hand-tested in Chromium with fake devices: a face video plus a wave in the top-right region passed the camera on its own; a still face showed "Your face is in view" and waited for the wave; the default fake camera (no face) passed only through "I can see myself"; a speech-like tone passed the mic in about 2 s and room noise ended in "We couldn't hear you clearly" after 20 s; a blocked permission showed the Chrome steps; voice-only showed one card and one checkbox; Start stored `interview@v1` and `biometric@v1` with the time. The only requests during the check were the MediaPipe files and model from our own host. Screenshots at 360, 768, 1024 and 1440 px, light and dark.
- Mobile Safari and Chrome: the Allow tap also starts the audio clock (iOS keeps audio suspended outside a tap), the preview is `playsInline` and muted, and iOS has its own fix steps. Not tried on a physical phone from the cloud container; worth a look on Darwin's phone.
- Defaults picked: the "I can see myself" fallback passes the camera even without a detected face (detection never blocks anyone); agreeing again replaces the stored consent; a biometric id sent for a voice-only interview is ignored. Until INTV-005, Start shows "You're all set".
- MediaPipe's WebAssembly logs an INFO line through `console.error`, which the Next dev overlay counts as an issue in local dev only.
