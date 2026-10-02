# APPLY-002: Candidate sign-in on the apply page

| Field | Value |
|---|---|
| Epic | APPLY — Apply |
| Milestone | M3 Intake |
| Status | In review |
| Size | S |
| Depends on | [APPLY-001](../APPLY/APPLY-001-public-apply-page.md), [AUTH-001](../AUTH/AUTH-001-employer-sign-in.md) |
| Requirements | FR-APPLY-02 |
| Gap areas | — |
| Design | Frame Apply (sign-in modal, header menu) |
| Docs to read | [`decisions/ADR-014-candidate-sso-only.md`](../../decisions/ADR-014-candidate-sso-only.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Candidates sign in with Google or Microsoft without losing their place or the source tag.

## Scope
**In:**
- Sign-in modal (browse vs apply intent)
- OAuth round-trip back to the apply page with form open
- Header signed-in menu + sign out
- Note for candidates without Google/Microsoft

**Out:**
- —

## Acceptance criteria
- [x] After sign-in with apply intent the form opens
- [x] `source` preserved
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

Plan auto-approved (the owner's standing rule: no plan approvals).

No API change: candidates sign in with Supabase Auth (Google or Microsoft, ADR-014) and the apply page reads the session itself, as AGENTS.md hard rule 3 allows. Candidate rows and the application itself are APPLY-003.

**Session on the page**
- The apply page (server) reads the session claims and passes the signed-in candidate (`candidateFromClaims()` in `lib/apply/session.ts`: id, name, email, provider) to a client `ApplySessionProvider` (`components/apply/apply-session.tsx`) that owns the modals. Only a Google or Microsoft session counts as a candidate; an email + password (TA) session sees the page signed out and signs in again with Google or Microsoft to apply.
- Apply now (both buttons): signed out → sign-in modal with the apply intent ("Sign in to apply", "…to apply for {role} at {company}"); signed in → the application modal.
- Header: "Sign in" (browse intent: "Sign in", "…to apply and follow your applications") when signed out; the signed-in menu (avatar, name from `md`; menu with name, email, "Signed in with Google/Microsoft", Sign out) when signed in, using the shell menu (dropdown from `md`, sheet on phones). Sign out ends the session on this device and keeps the candidate on the page.

**Sign-in modal** (frame Apply): the company mark, title and body by intent, Continue with Google / Continue with Microsoft, the "No password to create" note, a note for candidates without either account ("Contact {company} through their website to apply another way", linking the website when set), and the Terms / Privacy line like `/login`.

**OAuth round trip**
- `redirectTo` = `/auth/callback?next=/apply/{ws}/{slug}?apply=1&source={tag}&provider=…` (`applyReturnPath()`); `apply=1` only for the apply intent, `source` only when not direct (the tag is also kept in `sessionStorage` since APPLY-001).
- `/auth/callback` sends an apply-page `next` (`isApplyPath()`) straight back to it, skipping `/auth/continue` (which is the TA workspace routing). A cancelled or failed sign-in returns to the apply page with `signin=cancelled|failed`, which reopens the modal with the reason instead of landing on the employer login.
- Back on the page, `apply=1` with a candidate opens the application modal; the `apply` and `signin` parameters are then removed from the address bar (`source` stays).

**Application modal**: the frame's header ("Applying to {company}", role title) and signed-in account block ("Signed in with Google · we'll send updates here", "Not you?" signs out and reopens sign-in with the apply intent). The form fields are APPLY-003; until then the body says the form opens soon (replacing APPLY-001's placeholder dialog).

**Tests** (after hand testing): unit tests for `candidateFromClaims()`, `applyReturnPath()`, `isApplyPath()` and the callback's apply-page destinations. OAuth can't run in CI, so no Playwright journey.

## Log
_(Branch name, decisions, deviations, PR links, review files.)_

- 2026-10-02: branch `feature/apply-candidate-sign-in-vg9swx`. Plan auto-approved per the owner's rule.
- Decisions: only a Google or Microsoft session counts as a candidate (ADR-014); a TA user's email + password session sees the apply page signed out and signs in with Google or Microsoft to apply. The round-trip state (`apply=1`, `signin=…`) is read on the server, so the modal opens on first paint, and is removed from the address bar after, so a reload or shared link doesn't reopen it. A cancelled or failed sign-in returns to the apply page with the reason instead of the employer login. Candidates without either account are pointed to the employer's website (ADR-014), or told to contact the employer when no website is set. "Hiring with FastHyr" is hidden below `sm` to make room for the account control (the footer still names FastHyr). The Terms and Privacy links point at `/terms` and `/privacy` like `/login`; WEB-005 builds those pages.
- Deviation: the sign-in modal uses the kit `Dialog`, so the company mark sits beside the title rather than above it as in the frame.
- Follow-up for APPLY-003: replace the application modal's placeholder body with the form; the modal already shows the account and "Not you?".
- Tested by hand at 360, 768, 1024 and 1440 px, light and dark, with a local user given Google app metadata (OAuth itself can't run in the container): the authorize URL carries `next=/apply/…?apply=1&source=linkedin` (Microsoft adds `email profile`), the cancelled callback reopens sign-in with the reason and keeps `source`, the form opens after the round trip, the parameters are stripped, a reload doesn't reopen it, Sign out and "Not you?" keep the candidate on the page, and a TA password session sees Sign in.
