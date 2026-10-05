# INTV-007: Interview lifecycle: resume, expiry, reminders, re-invite, drop-off reasons

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M4 AI interview |
| Status | Ready |
| Size | M |
| Depends on | [INTV-005](../INTV/INTV-005-live-interview-ui-client.md), [MSG-003](../MSG/MSG-003-email-scheduling-and-sending-engine.md) |
| Requirements | FR-INTV-06, FR-INTV-08, FR-PIPE-11 |
| Gap areas | G1 |
| Design | Frames PipelineView (drop-offs), EmailTemplates |
| Docs to read | [`product/WORKFLOW.md §4–5`](../../product/WORKFLOW.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Candidates who don't start or finish are nudged, can resume, and TA teams see why and can re-invite.

## Scope
**In:**
- Abandon detection (missed heartbeats)
- Cron: expire links, send reminders, nudge unfinished
- Drop reason codes
- Re-invite API (single + all unfinished)
- Talk-time cap across attempts

**Out:**
- —

## Acceptance criteria
- [ ] Reminder only if pipeline toggle on and not started
- [ ] Re-invite supersedes old link
- [ ] Drop-off counts appear in analytics
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- The link page (INTV-002) already shows `expired` once `expires_at` passes and `unavailable` for a link with `superseded_by` set, so a re-invite only needs to set `superseded_by` on the old row.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
