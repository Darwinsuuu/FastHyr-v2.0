# Definition of Done

A task is Done only when **every applicable item** is true. Reviewers check this list.

## Functionality
- [ ] All acceptance criteria in the task file are met and ticked.
- [ ] Matches the canvas frame / screen spec (layout, copy, states: loading, empty, error, disabled, permission-denied).
- [ ] Copy follows `design/VOICE_AND_TONE.md`; strings live in `messages/en.json`.

## Correctness and safety
- [ ] **Tenancy:** every new endpoint is workspace-scoped through repositories and has a tenancy test (cross-workspace → 404; department scope respected).
- [ ] **Permissions** match `architecture/SECURITY.md`; UI hides what the API forbids.
- [ ] No personal data in URLs, logs or Sentry.
- [ ] Inputs validated server-side; errors return problem+json with a stable `code`.
- [ ] Credits and money only change through `services/credits.py` / billing services, inside transactions.
- [ ] AI calls go through `app/ai/`, use a versioned prompt + JSON schema, log to `ai_calls`; prompt changes include `ai_eval` results.
- [ ] G1–G9 impacts listed in the task are handled (e.g. bias rules for anything touching scoring).

## Quality
- [ ] Feature tested by hand against the acceptance criteria **before** writing unit tests.
- [ ] Unit tests cover the **important functional behaviour only** ([`TESTING_STRATEGY.md`](TESTING_STRATEGY.md)); no tests for UI details or trivial code.
- [ ] `make lint test` passes; types strict (mypy, tsc) with no new ignores.
- [ ] Migrations are reversible or expand-only, applied cleanly to a fresh DB, and match models.
- [ ] API client regenerated if the OpenAPI changed.
- [ ] Accessibility: keyboard path works, labels present, focus visible, contrast via tokens, reduced motion respected.
- [ ] Responsive and built mobile first: checked at 360, 768, 1024 and 1440 px; follows the patterns in [`design/RESPONSIVE.md`](../design/RESPONSIVE.md); touch targets ≥ 44 px; no horizontal page scroll.

## Docs
- [ ] Docs updated where behaviour, API, schema, env vars or decisions changed (same PR).
- [ ] Task file: branch name, implementation notes and any deviations recorded; BOARD.md updated.
- [ ] Branch was created from `develop` (not `release`/`master`); every commit has a subject **and** a What/Why/Task description ([`GIT_CONVENTIONS.md`](GIT_CONVENTIONS.md) §3); PR targets `develop`.
- [ ] PR description follows the standard template with every section filled (or "None").
