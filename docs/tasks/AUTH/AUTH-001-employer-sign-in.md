# AUTH-001: Employer sign-in

| Field | Value |
|---|---|
| Epic | AUTH — Authentication & workspaces |
| Milestone | M1 Access |
| Status | In review |
| Size | M |
| Depends on | [FND-005](../FND/FND-005-web-skeleton-hosts-tokens-fonts-auth-session-api-c.md), [FND-012](../FND/FND-012-ui-kit-design-system-components.md) |
| Requirements | FR-AUTH-01, FR-AUTH-04, FR-AUTH-09 |
| Gap areas | — |
| Design | Frame EmployerLogin |
| Docs to read | [`design/SCREENS.md`](../../design/SCREENS.md), [`architecture/SECURITY.md §1`](../../architecture/SECURITY.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users can sign in with Google, Microsoft or email + password and land in the right place.

## Scope
**In:**
- `/login` page as designed (split layout)
- OAuth + email/password via Supabase; `/auth/callback`
- Post-login routing (workspaces vs last active workspace; `next` param)
- Log out

**Out:**
- Password reset (AUTH-002)

## Acceptance criteria
- [x] Each method signs in and routes correctly
- [x] Errors shown inline (wrong password, provider cancelled)
- [x] Terms/Privacy links present
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- "New here?" — first sign-in creates the account

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Playwright: email sign-in happy path

## Implementation plan
Branch: `feature/employer-sign-in-58zkju` from `develop` (FND-005 and FND-012 merged).

- **`/login` (site host), frame EmployerLogin.** Built from the UI kit (`Button`, `Field`, `Input`) and tokens. Phone: a slim evergreen band with the logo, then the form full width. From `lg`: the split layout (evergreen panel with "For hiring teams", "Every applicant, heard." and the blurb on the left, form centred on the right, max 420 px). Google and Microsoft buttons with their marks, "or use your email" divider, Work email, Password, Continue, Terms of service and Privacy policy links (`/terms`, `/privacy`; those pages come with WEB-005). A signed-in visitor to `/login` goes straight on (see routing). "Forgot password?" is left out until AUTH-002 builds its modal, so there is no dead button.
- **Email + password, "New here?"** One Continue button. Passwords under 8 characters are stopped before any call. Continue tries `signInWithPassword`; on `invalid_credentials` it tries `signUp` with the same details. Supabase answers an existing email with a user that has no identities (no email sent), which we show as the wrong-password error; a real new account gets a verification email (confirmations are on, FR-AUTH-03) and the form shows "Check your email" inline. `email_not_confirmed` shows the same notice. The full `/verify-email` page with resend is AUTH-002.
- **Google and Microsoft.** `signInWithOAuth` back to `/auth/callback?next=…&provider=…`; Microsoft keeps the `email profile` scopes. The callback exchanges the code; if the provider sent an error (you cancelled or declined), it returns to `/login?error=cancelled&provider=…` and the page says "Sign-in with Google was cancelled. Try again or use another method." Any other failure shows the general error.
- **Post-login routing** in one place, `/auth/continue` (site host, client page) that every method goes through: a safe `next` wins (same app-host paths only, as today); otherwise it calls `/v1/me` and `/v1/me/workspaces`. No workspaces → `/workspaces` (Choose workspace). Otherwise the last active workspace: `last_workspace_id` from `/v1/me` if still a member, then the `fh_ws` cookie, then the first workspace; it sets `fh_ws` and opens the app host. Keeping `last_workspace_id` up to date on switch is AUTH-003.
- **`/workspaces` placeholder** (site host) with the user's name and Log out, so a new account doesn't land on a 404. AUTH-003 replaces it with the designed WorkspaceSelect.
- **Log out** (FR-AUTH-09): a shared `LogOutButton` (`components/auth/`) calling `signOut({ scope: "local" })` so only this device is signed out, clearing `fh_ws`, then back to `/login`. Used on the app placeholder and `/workspaces`; the DASH-001 user menu reuses it.
- **Copy** in `messages/en.json` (sentence case, no exclamation marks); the temporary login strings go.
- **Tests (after it works):** unit tests for the routing decision and the error-message mapping; Playwright email sign-in happy path against local Supabase (the repo has no Playwright yet, so this adds it to `apps/web` with one spec and a `make e2e` target, not run in CI until FND-006).
- **Checks by hand:** email sign-in (existing, wrong password, new account, unverified), Google and Microsoft buttons redirect correctly, cancelled provider message, `next` returns to the right page, log out; 360, 768, 1024 and 1440 px; Paper and Night.
- **Board:** mark FND-012 Done and AUTH-001 In review.

## Log
- 2026-09-28: plan approved by the owner; branch `feature/employer-sign-in-58zkju`.
- **No automatic resend for unverified accounts.** In the PKCE flow, `auth.resend()` replaces the code verifier stored in the browser even when Supabase refuses it (one email a minute), which breaks the link already sent. Signing in before verifying therefore only shows "Check your email"; resend with a cooldown comes with `/verify-email` in AUTH-002. An expired verification link returns to `/login` with "That link has expired or was already used."
- Local Supabase has phone confirmation off, so a sign-up for an existing email returns `user_already_exists` rather than the obfuscated user; both read as the wrong-password error.
- Choose workspace order: `last_workspace_id` (profile) → `fh_ws` cookie → first workspace. Nothing writes `last_workspace_id` yet; AUTH-003 does on switch.
- Night theme: the panel uses the `evergreen` token, which is a light mint in Night, with `on-evergreen` text. The frame only shows Paper.
- Terms and Privacy link to `/terms` and `/privacy`, which WEB-005 builds.
- Playwright is added now (`apps/web/e2e`, `make e2e` against `make dev`); TESTING_STRATEGY.md said REL-001, updated. Not in CI until FND-006.
- Found while testing: python-dotenv reads an empty value followed by a comment (`SUPABASE_JWKS_URL=   # …`) as the comment text, so a fresh copy of `apps/api/.env.example` failed at start-up with "Invalid JWKS URI scheme". Comments for empty values in that file now sit on the line above. README's `fasthyr` alias now uses the checkout's real folder case (`FastHyr-v2.0`); starting Next from a differently cased path on macOS breaks module resolution.
- Verified by hand with Chromium against local Supabase and the API: new email → "Check your email" → Mailpit link → `/workspaces`; password under 8 characters, wrong password (inline under Password), unverified account; `/login` while signed in goes straight on; signed-out `app…/pipelines?tab=live` → login → back to `/pipelines?tab=live` with `fh_ws` set to the profile's last workspace; Log out clears the session and `fh_ws`, and the app host then asks to sign in; Google and Microsoft buttons go to Supabase's authorize URL with the right callback (Microsoft with `email profile`); a cancelled provider shows "Sign-in with Microsoft was cancelled." No horizontal scroll at 360, 768, 1024 and 1440 px in Paper and Night. Real Google and Microsoft sign-in were not run here (they need the owner's OAuth apps).
- Tests: `lib/auth/destination.test.ts`, `lib/auth/password.test.ts`, `e2e/employer-sign-in.spec.ts`.
