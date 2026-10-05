# INTV-005: Live interview UI (client)

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M4 AI interview |
| Status | Ready |
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
- [ ] First AI utterance < 1.5 s after connect (p75)
- [ ] Captions for every AI question
- [ ] Mute pauses mic and shows status
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Playwright with fake media devices

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
