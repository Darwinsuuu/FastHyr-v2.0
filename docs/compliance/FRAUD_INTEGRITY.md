# Fraud and integrity (G7)

Scope decided in ADR-016. Technical detail in `architecture/MEDIA.md` §5 and `AI_PIPELINE.md` §5.

## 1. Threats
| Threat | MVP defence |
|---|---|
| Someone else takes the interview | Same Google/Microsoft account that applied must open the link (ADR-014); **same-face** check across the session (video); **second-voice** detection |
| Someone prompts the candidate off-camera | Second-voice detection; unusual timing |
| Candidate reads AI-generated answers | Read-aloud detection (delivery pattern + long pre-answer pauses) |
| Candidate leaves the frame / swaps seats | `no_face` and `different_face` flags |
| Link sharing | Link bound to the candidate's signed-in account |
| Replay of a recorded video / virtual camera | Post-MVP (liveness challenge) — the device-check "wave" is a light first step |
| ID-document fraud | Out of scope (no ID collection in MVP) |

## 2. Flag types
| Type | Label in UI | Evidence shown |
|---|---|---|
| `different_face` | "A different face appeared" | Timestamps + frame thumbnails (generated on demand, not stored long-term) |
| `no_face` | "Left the camera frame" | Time ranges |
| `second_voice` | "A second voice was heard" | Time ranges, jump-to buttons |
| `read_aloud` | "Answers sounded read aloud" | Answers affected with timestamps |
| `unusual_timing` | "Unusual response timing" | Latency chart vs session baseline |

## 3. Review workflow
1. Interviewed candidates with open flags appear under **Flagged** (Pipeline Candidates tab) and in Overview "Needs your attention".
2. The profile shows each flag with jump-to-moment controls and reviewer guidance: *"Flags can have innocent causes — someone else in the room, reading notes because of nerves or a disability. Listen to the marked moments before deciding."*
3. The reviewer marks **No concern** or **Concern confirmed** with a note. Confirming a concern does not reject; the TA still chooses Reject or Advance.
4. All resolutions go to `audit_log`; flag creation goes to `ai_decisions`.

## 4. Consent and privacy
- Integrity checks are disclosed in the interview consent; face checks need biometric consent (ADR-016, `PRIVACY.md`).
- Pipelines can switch integrity checks off ("Flag possible impersonation" toggle).

## 5. Tuning
Thresholds live in config. Target false-positive rate < 5% of interviews; review "No concern" rates monthly and adjust.
