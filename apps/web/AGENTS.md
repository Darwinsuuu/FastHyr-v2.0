# apps/web — frontend rules

Read [`/AGENTS.md`](../../AGENTS.md) first, then [`docs/architecture/FRONTEND.md`](../../docs/architecture/FRONTEND.md). This file repeats only the rules that matter on every change.

## Always
- **The browser talks to FastAPI only**, through the generated client in `packages/api-client` (plus Supabase Auth and signed Storage URLs). Never query Supabase tables or hand-write `fetch` calls to business endpoints.
- **No personal data in URLs.** IDs (UUIDs) only.
- **Mobile first:** base styles for a 360 px phone, then `sm:`…`2xl:` overrides ([`docs/design/RESPONSIVE.md`](../../docs/design/RESPONSIVE.md)).
- **Copy** lives in `messages/en.json`, sentence case, per [`docs/design/VOICE_AND_TONE.md`](../../docs/design/VOICE_AND_TONE.md).
- **UI gating** in `lib/permissions.ts` mirrors the API; it is never the only check.
- Candidates never see scores, signals or flags.
- TypeScript strict, no new `any` or ignores.

## Where things go (FND-005)
- Pages for the public site go in `app/site/`, TA app pages in `app/ta/` (`proxy.ts` maps the hosts; URLs never include `site` or `ta`).
- Style with token classes (`bg-surface`, `text-ink-muted`, `border-line-strong`, `type-heading`…); never raw hex. Change tokens in `docs/design/tokens.json`, then `pnpm --filter web tokens`.
- Data: `api` + `unwrap()` from `lib/api/client.ts` inside TanStack Query hooks; keys from `lib/api/keys.ts`.
- Copy: `t()` / `plural()` from `lib/i18n.ts` with keys in `messages/en.json`.
- Auth: `lib/supabase/` clients are for sign-in and the session only.

## Commands (from the repo root)
`make web` · `make lint-web` · `make test-web`

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
