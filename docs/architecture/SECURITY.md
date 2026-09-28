# Security

## 1. Authentication
- **Supabase Auth** issues JWTs; the API verifies signature (JWKS, cached), `exp`, `aud`, and `iss` on every request.
- TA users: Google, Microsoft (Azure), email + password (min 8 chars, breached-password check enabled in Supabase, email verification required).
- Candidates: Google, Microsoft only (ADR-014). The API treats a user as a candidate only on `/candidate/*` routes; being a candidate grants no TA access.
- Sessions: Supabase refresh tokens in secure, httpOnly cookies via `@supabase/ssr`; access token lifetime 1 h.
- Interview links carry a random 32-byte token (stored hashed); the page also requires the signed-in user to match the application's candidate.
- Invite and review-request tokens: random, hashed at rest, single-use, expiring.

## 2. Authorisation — permission matrix
Enforced in `app/core/permissions.py` (API) and mirrored in `apps/web/lib/permissions.ts` (UI only). "Scoped" = limited to the member's departments (Admins: all + No department).

| Action | Admin | Recruiter | Hiring manager |
|---|---|---|---|
| View Getting started / Overview | ✓ | ✓ (scoped) | ✓ (scoped, shortlist numbers only) |
| View pipelines list / pipeline dashboard / setup | ✓ | ✓ scoped | ✓ scoped |
| Create / edit draft / publish / duplicate pipeline | ✓ | ✓ scoped | — |
| Pause / resume / close / cancel / archive pipeline | ✓ | ✓ scoped | — |
| Top up pipeline credits (from free credits) | ✓ | ✓ scoped | — |
| View candidates in pipeline | all stages | all stages, scoped | Ready for review, Flagged, Advanced — scoped |
| View candidate profile, recording, transcript, download résumé/report | ✓ | ✓ scoped | shortlisted only, scoped |
| Reject / advance / invite manually / re-invite | ✓ | ✓ scoped | — |
| Resolve integrity flags / human-review requests | ✓ | ✓ scoped | — |
| Candidates pool | ✓ | ✓ scoped | shortlisted only, scoped |
| Ask Ava | ✓ | ✓ scoped | ✓ scoped (shortlist data only) |
| Email templates (view/edit) | ✓ | ✓ | — |
| Company profile, departments, members, invites | ✓ | view departments only | view departments only |
| Billing & invoices, buy credits, change plan | ✓ | — | — |
| Credit usage page | ✓ | read-only | — |
| Delete candidate data | ✓ | — | — |

Owner-only: none beyond Admin, except that the owner cannot be removed or demoted and ownership transfer is post-MVP.

Resource access failures return **404** (not 403) for resources outside the caller's workspace or scope.

## 3. Data protection
- TLS everywhere; Supabase encryption at rest; production backups with point-in-time recovery.
- Secrets only in Vercel/Render env vars; never in the repo; `.env*` git-ignored; gitleaks in CI.
- PII minimisation: provider scopes limited to email/profile; no PII in URLs, logs, Sentry breadcrumbs or analytics (scrub rules in Sentry; log IDs only).
- Redacted résumé text and transcripts are sensitive: access only through permissioned endpoints; never sent to Sentry.
- Biometric data (face embeddings) never persisted (ADR-016).

## 4. Application security
- Input validation with Pydantic; output encoding in React; email HTML sanitised (nh3 allow-list).
- File uploads: size/type checks, PDF sanitisation, no server-side rendering of untrusted PDFs except in the worker sandbox (text extraction only). SVG logos sanitised or rasterised.
- CORS: only the configured web origins. CSRF: API uses bearer tokens (no cookies) so CSRF doesn't apply; Next.js server actions are not used for business logic.
- Security headers on web (CSP with Stripe/Supabase/OpenAI Realtime origins allowed, HSTS, frame-ancestors none, Referrer-Policy strict-origin-when-cross-origin, Permissions-Policy allowing camera/microphone only on `/interview/*` and `/demo/*`).
- Rate limits (Redis): public apply endpoints, contact form, demo (per IP and global daily cap), auth-adjacent endpoints (invite accept, review request), Ava messages (per member).
- Bot protection on public forms and demo start (e.g. Cloudflare Turnstile).
- Webhooks: Stripe signature verification; Resend (Svix) signature verification; replay protection via event IDs.
- OpenAI Realtime client secrets are short-lived (≈1 min to connect) and scoped to one session; the server sets instructions (clients cannot change them because the server re-applies them via the sideband).
- Dependency scanning (Dependabot), `pip-audit`, `pnpm audit` in CI.

## 5. Audit log
`audit_log` records: member invited/removed/role changed; department created/renamed/deleted; pipeline published/paused/resumed/closed/cancelled/archived/topped up; candidate rejected/advanced/manually invited; flag resolved; review request resolved; template edited/reset/restored; plan changed; credits purchased; candidate data deleted; data exported (reports).

## 6. Incident basics
- Sentry alerts to the owner; runbooks in `docs/process/` (post-MVP expansion).
- Key rotation procedure: Supabase JWT secret, Stripe, OpenAI, Resend keys rotated via env vars with zero-downtime redeploy.
