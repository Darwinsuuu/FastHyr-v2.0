# FND-013: OpenAI integration layer

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | In review |
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
- [x] Invalid model output retried once then raises
- [x] Every call writes `ai_calls`
- [x] Unit tests run without network using fakes
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Unit tests for schema validation and logging

## Implementation plan
- **Schema**: `ai_calls` as in DATABASE.md, `status` in `ok|invalid_output|error`, nullable `cost_usd`, no FK on `entity_id`. RLS on, no policies.
- **Client** (`app/ai/client.py`): `OpenAIClient.structured(purpose, prompt, variables, schema, …)` calls the Responses API with the Pydantic schema as a strict JSON schema (`store=False`), validates `output_text`, retries once on an invalid answer (bad JSON, schema miss, refusal, incomplete) then raises `AIOutputError`. The SDK retries network errors, 429 and 5xx twice with `OPENAI_TIMEOUT_SECONDS`; after that `AIUnavailableError`. Every try writes an `ai_calls` row in its own session, with cost from `OPENAI_PRICES` (USD per million tokens per model; null when unpriced).
- **Prompts** (`app/ai/prompts.py`): `<name>@v<N>.md` with `# System` / `# User` sections and `${placeholders}` (`string.Template`, missing value = error); the tag `<name>@v<N>` is the logged prompt version.
- **Fake**: `AI_FAKE=1` → `FakeAIClient` answers from `app/ai/fixtures/<name>@v<N>.json`, validated and logged with model `fake`.
- **Eval**: `tests/ai_eval/` with `harness.py` (cases from `cases/<prompt>@vN/*.json`, range checks, counterfactual parity ±3, `run_case()` through the real client), skipped unless `AI_EVAL=1`.
- **Tests**: prompt loader unit tests; integration tests with a mock HTTP transport for the SDK (strict schema sent, valid answer logged with tokens and cost, one retry, two invalid answers raise, 5xx raises and logs, fake client).

## Log
- 2026-10-01: branch `feature/openai-integration` from `develop`. Plan auto-approved (Darwin's standing rule: no plan approvals).
- Decision: `responses.create` with an explicit strict JSON schema rather than `responses.parse`, so token usage is still logged when an answer fails validation.
- Decision: model prices are configuration (`OPENAI_PRICES`), not code, like the model names (ADR-007). Until they are set, `cost_usd` is null and tokens are still logged.
- Hand test: no OpenAI key in this environment, so the real client was exercised through a mock HTTP transport (same SDK request and response parsing), and `AI_FAKE` with a fixture. A first real call needs `OPENAI_API_KEY` and `OPENAI_TEXT_MODEL` (set with FND-007).
