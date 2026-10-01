# Prompts

One file per prompt version: `<name>@v<N>.md` (for example `resume_assessment@v1.md`), with a
`# System` section and a `# User` section. Placeholders are `${name}`. Never edit a released
version: copy it to `@v<N+1>`, change the caller, and run the evaluation set
(`tests/ai_eval/`). Output schemas live in `app/ai/schemas/`, fake outputs for `AI_FAKE=1` in
`app/ai/fixtures/<name>@v<N>.json`. Load with `app.ai.prompts.load_prompt(name, version)`.
