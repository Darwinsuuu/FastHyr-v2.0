# AUTH-005: User profile modal and account menu

| Field | Value |
|---|---|
| Epic | AUTH — Authentication & workspaces |
| Milestone | M1 Access |
| Status | In review |
| Size | S |
| Depends on | [DASH-001](../DASH/DASH-001-app-shell.md) |
| Requirements | FR-AUTH-08, FR-AUTH-09 |
| Gap areas | — |
| Design | Frame WorkspaceSelect (modal) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Users can see their account details and log out from anywhere.

## Scope
**In:**
- Account menu and profile modal (email verified, sign-in method, last sign-in, created, user ID copy)

**Out:**
- —

## Acceptance criteria
- [x] Modal matches design; copy button works; keyboard accessible
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
Size S: plan auto-approved (Darwin's standing rule, 2026-09-29).

**Data** (no new endpoint): the modal reads the user from Supabase Auth with `auth.getUser()` in the browser, which AGENTS.md hard rule 3 allows ("plus Supabase Auth") and which returns every field FR-AUTH-08 needs: email and `email_confirmed_at`, linked identities (sign-in methods), `last_sign_in_at`, `created_at`, `id`, and the provider's name and photo. `GET /v1/me` stays as it is, since the API would need read access to `auth.users` for the same data.
- `lib/auth/account.ts`: `accountDetails(user)` turns the Auth user into what the modal shows: name (provider full name, else the email), avatar, email, verified, sign-in methods in a fixed order (Google, Microsoft, Email and password; `azure` is Microsoft) with duplicates dropped, last sign-in, created, ID; and which provider the name and photo come from (Google or Microsoft, else none).

**Web**
- `components/auth/profile-dialog.tsx`: `ProfileDialog` on the UI kit `Dialog` (full-screen sheet on phones, 520 px dialog from `md`). Header: 64 px avatar, the name as the title, "Your FastHyr account". A definition list with Email (+ Verified badge, or Not verified), Signs in with (provider marks), Last signed in (date and time), Account created (date), User ID (mono, truncated, Copy button that reads "Copied" for 2 s and announces it). Stacked label-over-value below `md`, two columns (150 px labels) from `md`. Info note: "Your name and photo come from your {Google/Microsoft} account. To change them, update them in {provider} and sign in again." Email-only accounts get "Your account uses your email address as its name." Close button in the footer. Loading skeleton while Auth answers; an error line with Try again if it fails. Dates in the browser's time zone (this is the person's own account, not workspace data).
- `Dialog` gets an optional `leading` slot for the avatar next to the title.
- "User profile" entry (user-circle icon) above Log out in the app shell `UserMenu` (sidebar and top bar) and in the `/workspaces` account menu. Log out already works in both (FR-AUTH-09).

**Tests** (after testing by hand): unit tests for `accountDetails()` (provider mapping and order, verified flag, name fallback, note provider); e2e: open User profile from the app shell, check the email, sign-in method and ID, copy the ID, close with Escape and focus returns to the menu button. No new endpoint, so no tenancy test.

## Log
- 2026-09-29: branch `feature/user-profile-p4mhcl`. Plan auto-approved per Darwin's standing rule. No API change: the profile modal reads Supabase Auth directly (hard rule 3 allows Auth), so the task's tenancy test doesn't apply.
- 2026-09-29: built and tested by hand at 360, 768, 1024 and 1440 px, light and dark (screenshots in the project files under `screenshots/AUTH-005/`). The `/workspaces` page has no toast provider, so a failed copy shows an inline message under the ID instead of a toast. `Dialog` gained `leading` (avatar) and `returnFocusTo` (focus goes back to the account button, since the menu item that opened the dialog is gone), and its panel no longer draws a focus outline when it holds focus itself.
