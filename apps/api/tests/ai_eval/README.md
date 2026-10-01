# AI evaluation set (AI_PIPELINE.md §7)

Golden cases that run the real prompts against OpenAI, to check a prompt version before it
ships. They are skipped in normal test runs; run them with

    AI_EVAL=1 OPENAI_API_KEY=… OPENAI_TEXT_MODEL=… uv run pytest tests/ai_eval

Layout: `cases/<prompt>@v<N>/<case>.json`, each

    {"variables": {...}, "expect": {"<dotted.path>": [min, max]}, "pair": "<name>"}

`expect` gives the allowed range for numbers in the answer (for example
`"must_haves_met": [3, 4]`). Cases sharing a `pair` name are counterfactuals that differ only in
name, gender, age or school: their scores must be within ±3 points (`parity_gap()`). The prompt
tasks (SCREEN, INTV, ASMT) add their cases and a test module that calls `run_case()` with their
schema.
