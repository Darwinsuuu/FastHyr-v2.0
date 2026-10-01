"""The only code that calls OpenAI (ADR-007, AI_PIPELINE.md). Every text-model call goes through
`AIClient.structured()`: a versioned prompt from `prompts/`, a Pydantic output schema (sent as a
strict JSON schema), one retry on invalid output, and an `ai_calls` row per try."""
