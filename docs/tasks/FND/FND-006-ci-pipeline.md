# FND-006: CI pipeline

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | Done |
| Size | S |
| Depends on | [FND-005](../FND/FND-005-web-skeleton-hosts-tokens-fonts-auth-session-api-c.md) |
| Requirements | — |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/DEPLOYMENT.md §3`](../../architecture/DEPLOYMENT.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Every PR is checked automatically for lint, types, tests, migrations, API-contract drift and secrets.

## Scope
**In:**
- GitHub Actions: web job, api job (with Supabase Postgres service), db migration job, contract drift job, gitleaks, audits

**Out:**
- Deploy (FND-007)
- Playwright suite (REL-001)

## Acceptance criteria
- [ ] CI runs on PRs to master and blocks merge on failure
- [ ] Contract job fails if `packages/api-client` is stale
- [ ] Runtime < 10 min
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Open a PR with a deliberate lint error to verify failure

## Implementation plan
One workflow, `.github/workflows/ci.yml`, on PRs and pushes to `develop`, `release` and `master` (plus a manual run). Every step calls the same `make` target a contributor runs, so a red job reproduces locally. A composite action (`.github/actions/setup`) installs Node 24, pnpm and uv with caches. Five parallel jobs:
- **Web:** `make lint-web`, `make test-web`, `next build`.
- **API and database:** `make lint-api`; the pinned Supabase CLI starts a fresh stack (migrations and seed applied, unused services skipped); `make test-api` with `FASTHYR_REQUIRE_DB=1`; `make db-drift`. One job so Supabase starts once.
- **API client up to date:** `make api-client`, then `git diff --exit-code packages/api-client`.
- **Secrets and audits:** gitleaks (pinned release, checksum-verified) over full history; `pnpm audit --audit-level=moderate`; `pip-audit` on `uv export --locked`.
- **End-to-end:** Supabase + API + `next build`/`next start` with local env, then `make e2e`.

Config: the OAuth `env()` values in `supabase/config.toml` get dummy values in CI. `.gitleaks.toml` extends the default rules and allowlists only the two fixed local Supabase keys already in `tests/conftest.py`.

## Log
- Branch `feature/ci-0nm3iy`.
- Deviation: Playwright was out of scope (REL-001), but the suite exists since AUTH-001 and TESTING_STRATEGY.md planned it for this task, so the current specs run on every PR. REL-001 decides whether the full suite moves to `release` PRs plus nightly.
- Deviation: DEPLOYMENT.md listed a separate db job; the migration and drift checks share the API job so the stack starts once.
- Merge blocking is a GitHub setting: the owner adds the five checks as required status checks in the branch rules for `develop`, `release` and `master` (FND-007 covers the rest of branch protection).
- Checked locally before pushing: `make lint`, `make test-web`, `make test-api` (DB tests skip here), `make api-client` leaves no diff, `pnpm audit`, `pip-audit`, gitleaks (clean with the allowlist; 4 hits without it, all the local keys), web build and `next start` probe, actionlint on the workflow. The Supabase-backed steps are proven by the PR's own CI run (the build container hits Docker Hub rate limits).
