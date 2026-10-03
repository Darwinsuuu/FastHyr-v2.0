# INTV-002: Interview link page and states

| Field | Value |
|---|---|
| Epic | INTV — AI interview |
| Milestone | M4 AI interview |
| Status | Done |
| Size | M |
| Depends on | [SCREEN-003](../SCREEN/SCREEN-003-post-screen-actions-invite-or-schedule-rejection.md), [APPLY-002](../APPLY/APPLY-002-candidate-sign-in-on-the-apply-page.md) |
| Requirements | FR-INTV-02 |
| Gap areas | G1, G7 |
| Design | S-01 |
| Docs to read | [`design/SCREEN_SPECS.md S-01`](../../design/SCREEN_SPECS.md), [`decisions/ADR-014-candidate-sso-only.md`](../../decisions/ADR-014-candidate-sso-only.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Candidates opening their interview link always see the right next step.

## Scope
**In:**
- `interviews` table: already created by SCREEN-003 with every DATABASE.md column (token hash, status, expiry…); add only what this task finds missing
- `GET /candidate/interviews/{token}` with state resolution
- `/interview/[token]` page with every S-01 state
- Same-account check

**Out:**
- Device check (INTV-003)

## Acceptance criteria
- [x] Each S-01 state reachable in tests
- [x] Token lookup is constant-time on hash
- [x] Masked email shown on sign-in state
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
**API**
- No migration: SCREEN-003's `interviews` table has every column this task reads (`token_hash`, `status`, `drop_reason`, `expires_at`, `talk_seconds`, `superseded_by`).
- `GET /v1/candidate/interviews/{token}` takes an **optional** sign-in (new `OptionalCandidateDep`: no token, or a session that isn't Google/Microsoft, counts as signed out; a bad token is still 401). The link is opened before anyone signs in, so the not-signed-in state must come from the API.
- Lookup: SHA-256 of the token, one indexed equality lookup on the unique `token_hash` (`interviews_by_token_hash()`, deliberately unscoped like invite tokens: the token is the key), then `hmac.compare_digest` on the hashes. Unknown token → `404 interview_not_found`.
- State order in `services/interview_links.resolve()` (nothing personal before the account check):
  1. `unavailable`: link replaced by a re-invite (`superseded_by`), pipeline cancelled, application rejected or deleted candidate data.
  2. `expired`: not completed and `status = expired` or `expires_at` passed.
  3. `sign_in` (no candidate session, with the masked applying email `p•••@gmail.com`) / `wrong_account` (session's user ≠ the candidate's `auth_user_id`).
  4. `completed` (interview completed, or the application has moved past the interview).
  5. `technical_problem`: `drop_reason = technical_issue` (INTV-004/007 set it after 3 failed connections).
  6. `resume`: `in_progress` or `abandoned`, with minutes left of the 30-minute cap from `talk_seconds`.
  7. `welcome`: `not_started`.
- Response `InterviewLink`: `state`, `company {name, logo_url, website, careers_url}`, `job_title`, `format`, `expires_at`, `expires_label` (same wording as the email's `[Interview.expiry]`, `format_local()`), `first_name` (only after the account check), `masked_email` (only `sign_in`), `minutes_left` (only `resume`). Never a stage, score or flag.

**Web**
- `/interview/[token]` on the site host (`app/site/interview/[token]/page.tsx`): the server reads the session claims (`candidateFromClaims()`), calls the API with the access token when there is a candidate session, and renders `InterviewLinkPage` (`components/interview/`): header "{logo} {Company} · interviews with FastHyr", one centred S-01 card (max 640 px, `surface-raised`, `radius-lg`), mobile first.
- States per SCREEN_SPECS S-01. Sign in reuses the apply page's provider buttons; the OAuth round trip returns to `/interview/{token}` (`/auth/callback` accepts interview paths like apply paths; cancelled/failed come back with `?signin=` and the card says so). Wrong account: "Sign out and switch account" signs out on this device and reloads into the sign-in state.
- "Check my camera and mic", "Continue my interview" and "Try again" lead to a holding step until INTV-003 adds the device check. "I need an accommodation" links to the company's careers page or website (no contact email field yet, as the spec notes); hidden when there is neither. Unknown token → the site's not-found page.

**Tests** (after hand-testing): API integration tests reaching every state, the masked email, the hash lookup and the cross-workspace case (a candidate of another workspace with the token sees `wrong_account`, nothing personal); web unit tests for the callback path check.

**Defaults picked (not confirmed by Darwin):** expired and unavailable show without signing in (they say nothing personal); a replaced link reads as unavailable; "Technical problem" comes from `drop_reason = technical_issue`.

## Log
- Branch `feature/intv-002-interview-link-page-b88jxv`. Plan auto-approved (project rule).
- Built as planned. No migration. `GET /v1/candidate/interviews/{token}` (`OptionalCandidateDep`, `services/interview_links.py`, `interview_link_of()` in `repositories/interviews.py`); `/interview/[token]` on the site host (`components/interview/`, `lib/interview`); `/auth/callback` returns interview paths like apply paths.
- Tokens longer than 128 characters are `422 validation_failed`; the page treats them like unknown tokens (not found).
- The 30-minute cap for "minutes left" is `INTERVIEW_MINUTES` in `app/interview/plan.py`.
- Hand-tested every state signed out, as the applying Google account and as another one, light and dark, at 360, 768, 1024 and 1440 px (screenshots in the PR thread).
