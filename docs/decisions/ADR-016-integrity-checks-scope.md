# ADR-016: Integrity checks in MVP

- **Status:** Accepted
- **Date:** 2026-09-29

## Decision
When a pipeline has "Flag possible impersonation" on, the worker runs these checks after the interview:
1. **Same face throughout** (video only): sample frames, compute face embeddings locally, flag if a different face appears or if no face is visible for long stretches ("left the frame"). There is no ID-photo match.
2. **Second voice**: speaker separation on the recording; flag if another voice answers or prompts.
3. **Read-aloud answers**: transcript + timing heuristics (long silence then fluent, list-like delivery) analysed by a text model.
4. **Unusual timing**: response-latency outliers versus the session's own baseline.

Flags point to exact timestamps, **never reject a candidate on their own**, and must be reviewed by a person (Resolve: "No concern" / "Concern confirmed" with a note).

## Consequences
- Face embeddings are biometric data: computed in memory, never stored beyond the flag result, disclosed in the consent text (see `compliance/PRIVACY.md`). In jurisdictions with biometric laws (e.g. Illinois BIPA), face checks are off unless explicit biometric consent is captured — MVP captures it in the device-check consent.
