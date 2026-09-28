# FND-005: Web skeleton: hosts, tokens, fonts, auth session, API client

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | Backlog |
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
- [ ] Both hosts render a placeholder page locally
- [ ] Tokens available as Tailwind classes in both themes
- [ ] Authenticated call to `/me` works from the app host
- [ ] `make api-client` regenerates types
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Functional: date/time formatting in workspace time zone

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
