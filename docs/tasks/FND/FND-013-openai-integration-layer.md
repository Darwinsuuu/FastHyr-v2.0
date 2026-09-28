# FND-013: OpenAI integration layer

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | Backlog |
| Size | M |
| Depends on | [FND-004](../FND/FND-004-api-skeleton-auth-request-context-permissions-erro.md) |
| Requirements | NFR-08, NFR-09 |
| Gap areas | G2 |
| Design | — |
| Docs to read | [`decisions/ADR-007-openai-for-all-ai.md`](../../decisions/ADR-007-openai-for-all-ai.md), [`architecture/AI_PIPELINE.md §0, §7`](../../architecture/AI_PIPELINE.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
All AI calls go through one layer with versioned prompts, JSON-schema outputs, cost logging and test fakes.

## Scope
**In:**
- `app/ai/client.py` (Responses API structured outputs, retries, timeouts)
- Prompt loader for `prompts/<name>@vN.md`
- `ai_calls` migration + logging (tokens, cost, latency, model, prompt version)
- `AI_FAKE=1` fake client returning fixture outputs
- `tests/ai_eval/` harness skeleton

**Out:**
- Specific prompts (their tasks)
- Realtime (INTV-004)

## Acceptance criteria
- [ ] Invalid model output retried once then raises
- [ ] Every call writes `ai_calls`
- [ ] Unit tests run without network using fakes
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Unit tests for schema validation and logging

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
