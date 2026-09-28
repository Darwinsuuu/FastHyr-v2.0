# ADR-019: Three long-lived branches, three cloud environments, tests after the feature works

- **Status:** Accepted
- **Date:** 2026-09-29
- **Deciders:** Darwin Labiste (product owner)
- **Amends:** ADR-002 and ADR-003 (environment list)

## Decision
1. **Branches and environments**
   | Branch | Environment | Supabase project |
   |---|---|---|
   | `master` | Production | `fasthyr-prod` |
   | `release` | Release / QA testing | `fasthyr-qa` |
   | `develop` | Development testing | `fasthyr-dev` |
   **Every** branch is created from `develop`, and all code moves `develop` → `release` → `master` with no skipping and no back-merges. Bugs found in development or QA use `fix/`; bugs found in production use `hotfix/` — both from `develop`. There is no separate "staging" environment; QA on `release` plays that role.
2. **Feature branches** (`feature/<short-name>`, from `develop`) hold one commit, or a few when the work has clearly separate steps, formatted `feature(<short-name>): <step>` — e.g. `feature(auth-creation): Supabase auth integration`.
3. **Unit tests are written after the feature is tested by hand and works**, and cover **only the important functional behaviour** (business rules, credits/money, tenancy and permissions, security-sensitive logic, fixed bugs) — not full coverage.

## Consequences
- Details: `process/GIT_CONVENTIONS.md`, `process/TESTING_STRATEGY.md`, `architecture/DEPLOYMENT.md`.
- Three Supabase projects, three sets of Render services and Vercel domains to maintain.
- Tenancy tests stay mandatory for new endpoints because a cross-workspace leak is the highest-impact bug.
