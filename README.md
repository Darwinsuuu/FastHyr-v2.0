# FastHyr v2.0

**Every applicant, heard.** FastHyr is an AI interviewer for Talent Acquisition teams: share one apply link, and FastHyr screens every résumé, runs an adaptive video or voice interview with each qualified applicant, and delivers explainable assessments your team can act on.

- **Start here:** [`AGENTS.md`](AGENTS.md) (for people and AI agents alike)
- **Docs:** [`docs/README.md`](docs/README.md)
- **Task board:** [`docs/tasks/BOARD.md`](docs/tasks/BOARD.md)

Stack: Next.js · FastAPI · Supabase · OpenAI · Stripe · Resend · Vercel · Render.

## Quick start
Needs Node 24 (`.nvmrc`), pnpm 10 and [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 for you).

```bash
make setup   # install web and API dependencies
make dev     # web on http://localhost:3000, API on http://localhost:8000 (GET /health)
make lint    # ESLint, Prettier, tsc, ruff, mypy
make test    # Vitest and pytest
```

Other targets: `make web`, `make api`, `make api-client` (regenerate the TypeScript client from the API's OpenAPI schema). `make worker` and `make db-reset` arrive with FND-008 and FND-002.

Status: monorepo scaffold in place (FND-001); see the task board for what's next.
