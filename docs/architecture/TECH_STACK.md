# Tech stack

Pin major versions in lockfiles; upgrade deliberately. Anything not listed here needs a short justification in the PR (and an ADR if it's a platform choice).

## Platform (ADRs 001–009)
| Concern | Choice |
|---|---|
| Repo | Monorepo, pnpm workspaces (JS) + uv (Python), root `Makefile` |
| Web framework | Next.js (App Router), React, TypeScript (strict) |
| Web hosting | Vercel |
| API | FastAPI, Python 3.12, Pydantic v2, uvicorn |
| API + worker hosting | Render (Web Service, Background Worker, Key Value) |
| Auth | Supabase Auth (Google, Azure/Microsoft, email+password for TA) |
| Database | Supabase Postgres; SQL migrations via Supabase CLI |
| File storage | Supabase Storage (private buckets, signed URLs) |
| Jobs | arq + Redis |
| AI | OpenAI Realtime API (interview), Responses API with structured outputs (text), OpenAI transcription |
| Payments | Stripe (Billing, Payment Intents, Customer Portal, Stripe.js) |
| Email | Resend |

## Web (`apps/web`)
| Concern | Choice |
|---|---|
| Styling | Tailwind CSS with FastHyr design tokens as CSS variables (`design/DESIGN_SYSTEM.md`) |
| UI primitives | Radix UI primitives, wrapped as local components in `components/ui` (shadcn-style: code lives in the repo) |
| Icons | Phosphor Icons (Regular) — per design system |
| Fonts | Fraunces, Hanken Grotesk, IBM Plex Mono via `next/font/google` |
| Server state | TanStack Query + typed client from `packages/api-client` (openapi-typescript + openapi-fetch) |
| Forms | React Hook Form + Zod |
| Charts | Recharts, styled with tokens (custom SVG allowed for the funnel/flow shapes) |
| Rich text (email editor) | Tiptap (bold, italic, link, bullet list, parameter chips) |
| PDF viewing (résumé tab) | PDF.js (`react-pdf`) |
| Supabase | `@supabase/ssr` for auth session only |
| Stripe | `@stripe/stripe-js` for 3-D Secure confirmation |
| Tests | Vitest + Testing Library (unit), Playwright (e2e) |
| Lint/format | ESLint (next config), Prettier |

## API and worker (`apps/api`)
| Concern | Choice |
|---|---|
| DB access | SQLAlchemy 2 (async) + asyncpg; repositories enforce workspace scope |
| Validation / schemas | Pydantic v2 (request/response models = OpenAPI) |
| Auth | Supabase JWT verification via JWKS (`pyjwt`) |
| Jobs | arq (with cron) |
| OpenAI | `openai` Python SDK |
| Stripe | `stripe` Python SDK |
| Email | `resend` SDK; Jinja2 layout; `nh3` for HTML sanitising |
| PDF parsing | `pypdf` / `pdfplumber` for text; `pikepdf` for sanitising |
| PDF generation | WeasyPrint (HTML → PDF) |
| Media | `ffmpeg` (remux recording chunks, extract audio/frames) |
| Face checks | local face-embedding library (e.g. `insightface` / `face_recognition`) in the worker only |
| HTTP client | `httpx` |
| Rate limiting | Redis-backed limiter |
| Observability | Sentry SDK, structured JSON logs (`structlog`) |
| Tests | pytest, pytest-asyncio, a real Postgres from Supabase CLI for integration tests |
| Lint/format/types | Ruff (lint + format), mypy (strict on `app/`) |

## Environment variables (names only; values never committed)
```
# web
NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_URL,
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY, NEXT_PUBLIC_SITE_URL, NEXT_PUBLIC_APP_URL, SENTRY_DSN

# api + worker
DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWKS_URL,
REDIS_URL, OPENAI_API_KEY, OPENAI_REALTIME_MODEL, OPENAI_TEXT_MODEL, OPENAI_TRANSCRIBE_MODEL,
STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, RESEND_API_KEY, RESEND_WEBHOOK_SECRET,
WEB_ORIGINS, SENTRY_DSN, APP_ENV, TRIAL_CREDITS, TRIAL_DAYS, INTERVIEW_MAX_MINUTES, DEMO_MAX_MINUTES,
DEMO_DAILY_SPEND_CAP_USD
```
Each app keeps a `.env.example` listing every variable with a comment.
