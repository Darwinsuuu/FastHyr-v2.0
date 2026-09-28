# AGENTS.md — start here

This file is the entry point for any AI coding agent (Claude Code, Cursor, others) and for humans new to the repo. Read it fully before doing anything, then read only the docs your task links.

## What FastHyr is
FastHyr is a **B2B SaaS AI interviewer for Talent Acquisition (TA) teams**. A TA team creates a **pipeline** for a role, pastes its **apply link** into job posts (LinkedIn, JobStreet, Indeed, careers page…), and FastHyr runs the first round automatically:

1. Candidate signs in with Google/Microsoft and applies with a PDF résumé (1 credit used).
2. **Résumé screening** — explainable fit score against the pipeline's must-haves; pass → invited, fail → kind email with a human-review link.
3. **Adaptive AI interview** — live video + voice or voice only (OpenAI Realtime), personalised from the résumé and job, ≤ 30 minutes.
4. **Assessment** — weighted rubric scores with evidence and timestamps, integrity flags, summary.
5. TA reviews, then **advances** or **rejects**. A person makes every hiring decision.

Primary user: the TA/HR professional (customer). Secondary: hiring manager. End user: the candidate. Tagline: *Every applicant, heard.*

## Hard rules (never break these)
1. **No ATS/HRIS integrations**, ever. Candidates arrive only through a pipeline's apply link.
2. **Multi-tenant:** every piece of pipeline, candidate and assessment data is scoped to a **workspace**; queries go through workspace-scoped repositories; cross-workspace access returns 404. Department scoping applies inside a workspace.
3. **The browser talks to FastAPI only** (plus Supabase Auth and signed Storage URLs). No direct Supabase table access from the web app.
4. **Fairness:** name, photo, address, age, gender, graduation year and school name are never used in scoring; résumés are redacted before AI sees them; Ava refuses protected-attribute questions; integrity flags never reject anyone on their own.
5. **Explainable scores:** every score shows its calculation and evidence. Candidates never see scores, signals or flags.
6. **Credits and money** change only through the credits/billing services, inside transactions. 1 applicant = 1 credit, used on apply.
7. **All AI calls** go through `apps/api/app/ai/` with versioned prompts, JSON-schema outputs and cost logging.
8. **No personal data in URLs, logs or error reports.** IDs only.
9. **Decisions live in ADRs.** Don't silently change one — propose a new ADR.
10. **Every change is tied to a task** in `docs/tasks/`, and flags which gap areas (G1–G9) it touches.
11. **Responsive, mobile first.** Every page works from a 360 px phone up to desktop; write base styles for mobile and add larger breakpoints ([`docs/design/RESPONSIVE.md`](docs/design/RESPONSIVE.md)).

## Stack (fixed)
Monorepo · **Next.js** (App Router, TS) on **Vercel** · **FastAPI** (Python 3.12) + **arq worker** on **Render** (+ Redis) · **Supabase** Auth, Postgres, Storage · **OpenAI** (Realtime for interviews, Responses API for everything else) · **Stripe** · **Resend**. Details: [`docs/architecture/TECH_STACK.md`](docs/architecture/TECH_STACK.md).

## Branches and environments
`master` = production · `release` = QA testing · `develop` = development testing. Work happens on prefixed branches (`feature/`, `fix/`, `hotfix/`, `refactor/`, `perf/`, `test/`, `docs/`, `chore/`, `ci/`) with commits like `feature(auth-creation): …`; **every branch starts from `develop`** (never `release` or `master`) — QA bugs use `fix/`, production bugs use `hotfix/`; **all code goes `develop` → `release` → `master`, no skipping**. Full rules: [`docs/process/GIT_CONVENTIONS.md`](docs/process/GIT_CONVENTIONS.md).

## Repository map
```
AGENTS.md            ← you are here      CLAUDE.md  ← imports this file
apps/web/            Next.js app (+ apps/web/AGENTS.md)       [created in FND-001]
apps/api/            FastAPI API + worker (+ apps/api/AGENTS.md) [created in FND-001]
packages/api-client/ generated TypeScript client
supabase/            migrations, seed, config
docs/                everything below
```

## Documentation map
| Need | Read |
|---|---|
| Docs index and reading order | [`docs/README.md`](docs/README.md) |
| What we're building and why | [`docs/product/BRD.md`](docs/product/BRD.md) |
| Exact words to use | [`docs/product/GLOSSARY.md`](docs/product/GLOSSARY.md) |
| Pipeline and application states | [`docs/product/WORKFLOW.md`](docs/product/WORKFLOW.md) |
| Requirements (FR/NFR IDs) | [`docs/product/REQUIREMENTS.md`](docs/product/REQUIREMENTS.md) |
| Gap areas G1–G9 | [`docs/product/CONSIDERATIONS.md`](docs/product/CONSIDERATIONS.md) |
| Milestones and open questions | [`docs/product/ROADMAP.md`](docs/product/ROADMAP.md) |
| System design | [`docs/architecture/`](docs/architecture/) — start with `ARCHITECTURE.md` |
| Compliance, privacy, bias, integrity | [`docs/compliance/`](docs/compliance/) |
| Screens, design system, copy | [`docs/design/`](docs/design/) — `SCREENS.md` maps every screen to a route and task |
| Decisions | [`docs/decisions/`](docs/decisions/) |
| How we work, DoD, git | [`docs/process/`](docs/process/) |
| Task board and task files | [`docs/tasks/BOARD.md`](docs/tasks/BOARD.md) |
| Reviews | [`docs/reviews/`](docs/reviews/) |

Design: Claude Design canvas "FastHyr — Product Design" (https://claude.ai/artifact/5K5XeumMMTTgj4f37pzwvW) and the FastHyr Design System (https://claude.ai/artifact/1zb54CSHVs2p3tV1dTM1mt). How to read them: [`docs/design/DESIGN_SOURCES.md`](docs/design/DESIGN_SOURCES.md).

## How to work on a task
1. Open [`docs/tasks/BOARD.md`](docs/tasks/BOARD.md); pick a `Ready` task (dependencies done).
2. Read the task file and **only** the docs it links. Write the "Implementation plan" section; get approval for M/L tasks.
3. **Always** create the branch from `develop` (never `release` or `master`): `git checkout develop && git pull && git checkout -b feature/<short-name>`; one commit or a few meaningful ones, e.g. `feature(auth-creation): Supabase auth integration`, **each with a What / Why / Task description and no AI co-author lines** (AI tools are credited only in the PR description they create) ([`docs/process/GIT_CONVENTIONS.md`](docs/process/GIT_CONVENTIONS.md)).
4. Build and **test by hand** until the acceptance criteria pass; **then** write unit tests for the important functional behaviour only ([`docs/process/TESTING_STRATEGY.md`](docs/process/TESTING_STRATEGY.md)). Meet [`docs/process/DEFINITION_OF_DONE.md`](docs/process/DEFINITION_OF_DONE.md); update docs in the same PR; open the PR into `develop` with the **full standard description** from [`.github/pull_request_template.md`](.github/pull_request_template.md).
5. A fresh session reviews and writes `docs/reviews/<TASK-ID>-r<N>.md`. Full loop: [`docs/process/DEV_WORKFLOW.md`](docs/process/DEV_WORKFLOW.md).

When sources disagree: **ADRs > REQUIREMENTS.md > SCREEN_SPECS.md > canvas frame > other docs.** Ask the product owner one question at a time when a product decision is needed.

## Tone
Warm, professional, reassuring for candidates; efficient and evidence-first for TA users. Sentence case, no emoji, no exclamation marks. See [`docs/design/VOICE_AND_TONE.md`](docs/design/VOICE_AND_TONE.md).

## Current status
Documentation complete for the MVP (2026-09-29). No application code yet — next task: **FND-001 Monorepo scaffold**.
