# Fake outputs

With `AI_FAKE=1`, `FakeAIClient` answers a call for prompt `<name>@v<N>` with the JSON in
`<name>@v<N>.json` here, validated against the call's schema. Each prompt task adds one fixture
so the app runs end to end without OpenAI (local development, CI, e2e).

A prompt whose answer must mirror its input (one result per pipeline criterion, quotes taken from
the résumé, as `resume_assessment@v1`) registers a builder in `app/ai/fakes.py` instead.
