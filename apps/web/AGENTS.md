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

## Commands (from the repo root)
`make web` · `make lint-web` · `make test-web`

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
