# INTV-003: Device check and consent

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M4 AI interview |
| Status | Backlog |
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
- [ ] Start disabled until checks + required consents
- [ ] Works on mobile Safari/Chrome
- [ ] No media leaves the browser during the check
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Manual matrix across browsers

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
