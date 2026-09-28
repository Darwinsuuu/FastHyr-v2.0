# FND-005: Web skeleton: hosts, tokens, fonts, auth session, API client

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | In review |
| Size | M |
| Depends on | [FND-004](../FND/FND-004-api-skeleton-auth-request-context-permissions-erro.md) |
| Requirements | NFR-06, NFR-12 |
| Gap areas | — |
| Design | All frames (tokens) |
| Docs to read | [`architecture/FRONTEND.md`](../../architecture/FRONTEND.md), [`design/DESIGN_SYSTEM.md`](../../design/DESIGN_SYSTEM.md), [`design/tokens.json`](../../design/tokens.json) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
The Next.js app serves the site and app hosts, has the FastHyr look (tokens, fonts, themes) and can call the API as the signed-in user.

## Scope
**In:**
- Host middleware: `(site)` vs `(app)` route groups; app host redirects to login when signed out
- Mobile-first setup: Tailwind default breakpoints, base styles for 360 px, viewport meta, safe-area utilities
- Script generating `styles/tokens.css` (Paper + Night) from `docs/design/tokens.json`; Tailwind theme mapping
- Fonts via next/font (Fraunces, Hanken Grotesk, IBM Plex Mono)
- `@supabase/ssr` session handling (auth only)
- openapi-typescript + openapi-fetch client in `packages/api-client`, TanStack Query provider, `X-Workspace-Id` from cookie
- `messages/en.json` + tiny i18n helper; locale/time-zone formatters

**Out:**
- Components (FND-012)
- Real pages

## Acceptance criteria
- [x] Both hosts render a placeholder page locally
- [x] Tokens available as Tailwind classes in both themes
- [x] Authenticated call to `/me` works from the app host
- [x] `make api-client` regenerates types
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Functional: date/time formatting in workspace time zone

## Implementation plan
Branch: `feature/web-skeleton` from `develop` after FND-004 (PR #5) merged.

- **Hosts:** `proxy.ts` (Next 16's name for middleware) rewrites the app host (`NEXT_PUBLIC_APP_URL`) into the TA folder and everything else into the site folder; signed-out app visitors go to `<site>/login?next=<path>`; the proxy also refreshes the Supabase session. Placeholder pages: site home, a temporary login (email + password, Google, Microsoft with `email profile` scopes) with `/auth/callback`, and an app page showing `/v1/me` and `/v1/me/workspaces`. AUTH-001 replaces the login page.
- **Look:** `scripts/generate-tokens.mjs` writes `styles/tokens.css` (Paper + Night variables, Tailwind v4 `@theme` mapping, `type-*` utilities) from `docs/design/tokens.json`; lint fails when stale. next/font for Fraunces, Hanken Grotesk, IBM Plex Mono. Mobile-first base styles (gutters, safe areas, 16 px inputs, focus ring, reduced motion). Theme follows the system with a `data-theme` override.
- **API:** `packages/api-client` `createApiClient({ baseUrl, getAccessToken, getWorkspaceId })` adds `Authorization` and `X-Workspace-Id`; `unwrap()` throws `ApiError` with the problem+json `code`. `lib/supabase/` (auth only), `lib/api/` (client, keys, TanStack Query provider, workspace switch), `fh_ws` cookie.
- **Copy and formatting:** `messages/en.json` + `t()`; `lib/format` with the workspace time zone.
- **Deviation flagged to the owner:** session cookies are readable by the page (the browser sends the token to FastAPI), so SECURITY.md's "httpOnly" line is corrected.
- **Tests:** time-zone formatting, host routing and redirects, token output, API client headers and errors.

## Log
- 2026-09-28: plan approved by the owner; branch `feature/web-skeleton`; PR #6.
- Host folders are `app/site/` and `app/ta/` rather than the `(site)`/`(app)` route groups in FRONTEND.md: route groups don't change URLs, so both can't own `/`. URLs never show the folder names.
- In dev, Next gives the proxy `http://localhost:3000` as the request URL whatever the Host header, and shortens a redirect to that origin into `/login`, which the browser resolved on the app host and looped. Signed-out app requests are therefore rewritten to `app/ta/sign-in-required`, a route handler whose redirect keeps the full site URL; the wanted path travels in the `x-fh-next-path` request header.
- **Local hosts changed** to `fasthyr.localhost:3000` and `app.fasthyr.localhost:3000` with `NEXT_PUBLIC_COOKIE_DOMAIN=fasthyr.localhost`. Chromium treats `Domain=localhost` as host-only, so a sign-in on `localhost` never reached `app.localhost`; under `fasthyr.localhost` the cookie is shared (verified). Updated the web and API env examples, the API's default `WEB_ORIGINS`, and Supabase `site_url` / redirect allow-list. Safari needs an `/etc/hosts` line (README).
- `getClaims()` in the proxy verifies the session token against the project's JWKS (ES256 locally) without a round trip to Auth.
- Plural copy: `plural(key, count)` with `{ one, other }` entries in `messages/en.json`.
- Verified by hand with Chromium against local Supabase and the API: signed-out `app.fasthyr.localhost/pipelines?tab=x` → `fasthyr.localhost/login?next=%2Fpipelines%3Ftab%3Dx`; email sign-in lands on the app host, which shows the user and their workspace from `/v1/me` and `/v1/me/workspaces`; no horizontal scroll at 360, 768, 1024 and 1440 px; Paper and Night both render; Fraunces, Hanken Grotesk and Plex Mono load; `next build` succeeds. Google and Microsoft sign-in were not run here (they need the owner's OAuth apps); the Microsoft button asks for `email profile`.
- Tests: `lib/format/format.test.ts`, `lib/hosts.test.ts`, `lib/i18n.test.ts`, `lib/workspace.test.ts`, `lib/api/api-client.test.ts`, `scripts/tokens.test.ts`.
