# AUTH-002: Password reset and email verification

| Field | Value |
|---|---|
| Epic | AUTH — Authentication & workspaces |
| Milestone | M1 Access |
| Status | Done |
| Size | S |
| Depends on | [AUTH-001](../AUTH/AUTH-001-employer-sign-in.md), [FND-010](../FND/FND-010-email-infrastructure-resend.md) |
| Requirements | FR-AUTH-02, FR-AUTH-03 |
| Gap areas | — |
| Design | Frame EmployerLogin (modal), S-05, S-06 |
| Docs to read | [`design/SCREEN_SPECS.md S-05, S-06`](../../design/SCREEN_SPECS.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Password users can recover access and must verify their email before using a workspace.

## Scope
**In:**
- Forgot-password modal states (form, sending, sent, resend 60 s)
- `/reset-password` (S-05)
- `/verify-email` (S-06)
- Supabase email templates via Resend SMTP

**Out:**
- —

## Acceptance criteria
- [x] Reset link single-use, 1 h expiry
- [x] Response never reveals whether an email exists
- [x] Unverified users can't create/join workspaces
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
Branch: `feature/password-reset-verify-wvkxgc` from `develop` (AUTH-001 merged). Size S, so no plan sign-off round; the owner asked to proceed.

- **Links that work in any browser.** Supabase's default links use the PKCE code, which only works in the browser that asked for the email and breaks when a resend replaces the stored verifier (AUTH-001 log). The confirmation and recovery templates instead link to a new `/auth/confirm?token_hash=…&type=…` route on the site host, which calls `verifyOtp` on the server and sets the session. Verification goes on to `/auth/continue` (keeping `next`); recovery goes to `/reset-password`; a used or expired token goes to the "expired" state of each page. `/auth/callback` stays for Google and Microsoft.
- **Forgot-password modal** (frame EmployerLogin) from the kit `Dialog`: a "Forgot password?" link beside the Password label opens it with the typed email. States: form (email check "Enter your work email." / "Enter a valid email, like you@company.com."), sending, sent ("If an account exists for {email}…", link works once, expires in 1 hour) and "Resend link" with a 60 s countdown. Every answer from Supabase, including "too many emails", shows the sent state, so the response never reveals whether an account exists; only a network failure shows an error.
- **`/reset-password` (S-05)** in the split layout: New password (min 8, show/hide) and Confirm password, "Save password" → `updateUser` → `/auth/continue`. The spec says `/workspaces`; `/auth/continue` sends people with no workspace there and everyone else to their last workspace, as FR-AUTH-04 says (REQUIREMENTS wins over SCREEN_SPECS). No recovery session or a failed link shows "This link has expired or was already used." with "Send a new link", which opens the same modal.
- **`/verify-email` (S-06)**: after a new sign-up, or signing in before verifying, the login form stores the email in `sessionStorage` (never in the URL, hard rule 8) and opens this page. "Check your email · We sent a link to {email}…", "Resend link" with a 60 s cooldown that survives a reload (`auth.resend`, safe now that links don't depend on the stored verifier), and "Use a different email" (logs out, back to `/login`). No stored email → `/login`. The inline "Check your email" block in the login form goes.
- **Unverified users can't create or join workspaces (FR-AUTH-03).** With confirmations on, Supabase gives no session before verification. On top of that: `/auth/continue` sends an unverified session to `/verify-email`, and the API gets a `VerifiedUser` dependency returning `403 email_not_verified`, for AUTH-003's create and join endpoints to use (none exist yet).
- **Email templates** in `supabase/templates/` (confirmation, recovery), branded and short, set in `config.toml` with subjects. Local mail still goes to Mailpit; `[auth.email.smtp]` for Resend stays off locally and a guide covers turning it on for hosted projects (FND-010 isn't needed: Supabase sends these itself). Link expiry stays 1 hour (`otp_expiry = 3600`), resend 60 s (`max_frequency`).
- **Tests (after it works):** unit tests for the reset request mapping (never reveals the account), the confirm route's redirects, and the verify-email storage/cooldown helper; API unit test for `email_not_verified`; Playwright: forgot password → Mailpit link → new password → signed in.
- **Checks by hand:** reset happy path, used link, expired/garbled link, mismatch and short passwords, resend countdowns, verify-email after sign-up and resend, "Use a different email"; 360, 768, 1024, 1440 px; Paper and Night.
- **Board:** AUTH-001 Done, AUTH-002 In review.

## Log
- 2026-09-29: branch `feature/password-reset-verify-wvkxgc`; the owner asked to go ahead (size S).
- **FND-010 isn't needed.** Supabase Auth sends these emails through its own SMTP setting, not the API's email service. Locally Mailpit catches them; hosted projects get Resend SMTP from the dashboard (DEPLOYMENT.md, "Auth emails").
- **Token-hash links.** Both templates link to `/auth/confirm?token_hash=…&type=…`, verified on the server with `verifyOtp`. The link works in any browser, and a resend no longer breaks an earlier link (the AUTH-001 PKCE problem). The confirmation link keeps `next` by building on `{{ .RedirectTo }}`, which the web always sets to `/auth/confirm?next=…`. `/auth/callback` now only handles Google and Microsoft. Known trade-off of any single-use GET link: a mail scanner that opens links can use it up; the page then offers a new one.
- **Never revealing an account.** Supabase returns success for unknown emails but `429` for a second reset to a real account within a minute, so the modal treats every answer from Supabase as "sent"; only no answer at all shows an error.
- **After saving a new password** the user goes to `/auth/continue`, not `/workspaces` as S-05 says, so people with a workspace land in it (FR-AUTH-04 wins over the spec).
- **`/verify-email`** gets the address from `sessionStorage` (never the URL); a direct visit with nothing stored goes to `/login`. The cooldown survives a reload. The sign-in form's email field stays uncontrolled so text typed before hydration isn't lost; "Forgot password?" copies its value into the modal.
- **FR-AUTH-03 on the API.** `VerifiedUserDep` (`app/api/deps.py`) raises `403 email_not_verified` when the token's `user_metadata.email_verified` isn't true. No endpoint uses it yet: AUTH-003's create and join endpoints must. Checked locally that Supabase sets `email_verified: true` in the token after an email is confirmed.
- A signed-in user who opens `/reset-password` directly can set a password without the old one (`secure_password_change = false`, unchanged).
- Found while testing: `make e2e` clicks sometimes landed before `next dev` hydrated the page and did nothing (the AUTH-001 Log out step too); `e2e/hydration.ts` retries the click until the page reacts.
- Verified by hand with Chromium against local Supabase: sign-up → `/verify-email` (cooldown survives reload, resend sends a second email, "Use a different email" returns to login, direct visit without storage → login) → Mailpit link keeps `next`; forgot password with the typed email, empty and invalid email messages, unknown email and a second request within a minute both show "sent"; reset link opened in a different browser → new password (short, mismatch and same-as-current errors) → signed in; the same link again → expired state → "Send a new link" opens the modal; sign in with the new password. No horizontal scroll at 360, 768, 1024 and 1440 px, Paper and Night.
- Tests: `lib/auth/recovery.test.ts`, `lib/auth/links.test.ts`, `lib/auth/pending-verification.test.ts`, `tests/unit/test_auth.py` (verified-user check), `e2e/password-reset.spec.ts`.
