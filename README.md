# FastHyr v2.0

**Every applicant, heard.** FastHyr is an AI interviewer for Talent Acquisition teams: share one apply link, and FastHyr screens every résumé, runs an adaptive video or voice interview with each qualified applicant, and delivers explainable assessments your team can act on.

- **Start here:** [`AGENTS.md`](AGENTS.md) (for people and AI agents alike)
- **Docs:** [`docs/README.md`](docs/README.md)
- **Task board:** [`docs/tasks/BOARD.md`](docs/tasks/BOARD.md)

Stack: Next.js · FastAPI · Supabase · OpenAI · Stripe · Resend · Vercel · Render.

## Run locally

### 1. Install the tools (once)
| Tool | Version | Install (macOS) |
|---|---|---|
| Node.js | 24 LTS (pinned in `.nvmrc`) | `brew install nvm`, then `nvm install 24 && nvm use 24` |
| pnpm | 10 (pinned in `package.json`) | `corepack enable` (ships with Node), or `npm install -g pnpm@10` |
| uv | latest | `brew install uv` (it downloads Python 3.12 by itself) |
| make | any | included with Xcode Command Line Tools (`xcode-select --install`) |

Check them with `node -v` (v24.x), `pnpm -v` (10.x) and `uv --version`. If `nvm` is not found after installing it, follow the shell setup lines that `brew info nvm` prints.

### 2. Install dependencies
From the repository root (run again after pulling changes that add packages):
```bash
make setup   # pnpm install + uv sync in apps/api
```

### 3. Environment variables (optional for now)
Both apps run with defaults. To override, copy the examples; `.env` files are never committed.
```bash
cp apps/web/.env.example apps/web/.env.local
cp apps/api/.env.example apps/api/.env
```

### 4. Start the apps
```bash
make dev     # web and API together; Ctrl+C stops both
```
| What | URL |
|---|---|
| Web app | http://localhost:3000 |
| API health check | http://localhost:8000/health → `{"status":"ok"}` |
| API docs (Swagger) | http://localhost:8000/docs |

Run one app at a time with `make web` or `make api`. Web changes reload in the browser and the API restarts on save.

### 5. Test the UI at different screen sizes
In Chrome, open DevTools (Cmd+Option+I / Ctrl+Shift+I), turn on the device toolbar (Cmd+Shift+M / Ctrl+Shift+M) and check 360, 768, 1024 and 1440 px wide, as the [Definition of Done](docs/process/DEFINITION_OF_DONE.md) requires.

### 6. Lint and tests
```bash
make lint    # Prettier, ESLint, tsc, ruff, mypy
make test    # Vitest (web) and pytest (API)
```

### Other commands
| Command | What it does |
|---|---|
| `make api-client` | Regenerates the TypeScript client in `packages/api-client` from the API's OpenAPI schema |
| `make worker` | Background worker (added in FND-008) |
| `make db-reset` | Resets the local Supabase database (added in FND-002) |

### Troubleshooting
| Problem | Fix |
|---|---|
| `make: pnpm: No such file or directory` | Run `corepack enable` (or `npm install -g pnpm@10`), then `make setup` |
| `Unsupported engine` warning | Switch to Node 24 with `nvm use` |
| `Address already in use` on :3000 or :8000 | Another dev server is running; stop it, or find it with `lsof -i :3000` |
| Web shows old code after pulling | Stop `make dev`, run `make setup`, start again |

Status: monorepo scaffold in place (FND-001); see the task board for what's next.
