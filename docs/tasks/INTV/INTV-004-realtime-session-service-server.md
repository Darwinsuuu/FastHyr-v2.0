# INTV-004: Realtime session service (server)

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M4 AI interview |
| Status | Backlog |
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
- [ ] Session can't exceed cap even if client misbehaves
- [ ] Instructions contain fairness rules
- [ ] Resume continues from the next topic
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Keep the provider behind an interface for testing
- The link page (INTV-002) reads `interviews.status`, `talk_seconds` and `drop_reason`: set `in_progress`/`abandoned` and `talk_seconds` as attempts run, and `drop_reason = technical_issue` after 3 failed connections so the page shows "We couldn't connect you". Look links up with `services/interview_links` (`hash_token` + `interview_link_of()`).

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Integration test with a fake Realtime server

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
