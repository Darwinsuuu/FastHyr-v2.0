# FND-007: Deployments: Vercel, Render blueprint, dev and QA environments

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | Backlog |
| Size | M |
| Depends on | [FND-006](../FND/FND-006-ci-pipeline.md), [FND-008](../FND/FND-008-background-worker-and-job-framework.md) |
| Requirements | NFR-05 |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/DEPLOYMENT.md`](../../architecture/DEPLOYMENT.md), [`decisions/ADR-003-hosting-vercel-render.md`](../../decisions/ADR-003-hosting-vercel-render.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
The development (`develop`) and QA (`release`) environments run end to end in the cloud: web on Vercel, API + worker + Redis on Render, their own Supabase projects — deployed from Git.

## Scope
**In:**
- `render.yaml` with api, worker, key value; health checks
- Vercel project with both hosts and env vars
- Protect `master`, `release`, `develop` (PR-only, CI required)
- Migration workflow (auto dev and QA, manual approval prod)
- Domains/DNS for dev and QA (owner action)

**Out:**
- Production cut-over (REL-003)

## Acceptance criteria
- [ ] Merge to `develop` deploys the development environment; merge to `release` deploys QA
- [ ] App host on each environment signs in and calls the API
- [ ] Migrations applied by workflow per environment
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Keep production services defined but scaled to zero/paused until launch if cost matters

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Manual smoke test on the development and QA environments

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
