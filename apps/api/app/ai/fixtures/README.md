# Fake outputs

With `AI_FAKE=1`, `FakeAIClient` answers a call for prompt `<name>@v<N>` with the JSON in
`<name>@v<N>.json` here, validated against the call's schema. Each prompt task adds one fixture
so the app runs end to end without OpenAI (local development, CI, e2e).
