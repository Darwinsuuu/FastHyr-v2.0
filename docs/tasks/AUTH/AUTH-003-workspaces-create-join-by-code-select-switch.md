# AUTH-003: Workspaces: create, join by code, select, switch

| Field | Value |
|---|---|
| Epic | AUTH — Authentication & workspaces |
| Milestone | M1 Access |
| Status | In review |
| Size | M |
| Depends on | [AUTH-001](../AUTH/AUTH-001-employer-sign-in.md), [FND-003](../FND/FND-003-core-schema-identity-workspaces-members-department.md), [BILL-002](../BILL/BILL-002-credit-ledger-service.md) |
| Requirements | FR-AUTH-04, FR-AUTH-05, FR-AUTH-06, FR-AUTH-07 |
| Gap areas | — |
| Design | Frame WorkspaceSelect, app shell switcher |
| Docs to read | [`architecture/MULTI_TENANCY.md`](../../architecture/MULTI_TENANCY.md), [`decisions/ADR-005-tenancy-and-roles.md`](../../decisions/ADR-005-tenancy-and-roles.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
A signed-in TA user can create a workspace (becoming owner with trial credits), join one with a code, and switch between workspaces.

## Scope
**In:**
- `/workspaces` page
- `POST /workspaces` (slug generation, owner membership, company profile stub, trial grant, default email templates hook)
- Join by code from this page (uses invite accept API)
- Active workspace cookie + `profiles.last_workspace_id`

**Out:**
- Invite link page (AUTH-004)

## Acceptance criteria
- [ ] Creating a workspace grants 20 trial credits (recorded now; the credits arrive with BILL-002) and opens Getting started (placeholder until DASH-002)
- [x] Switching clears cached data
- [x] Slug unique and URL-safe
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Integration tests for create/join

## Implementation plan
Branch: `feature/choose-workspace-5dvi3p` from `develop` (AUTH-001 and AUTH-002 merged).

**Dependencies not done yet, and what this task does instead**
- **BILL-002 (credit ledger) isn't built.** `POST /workspaces` sets `workspaces.trial_granted_at` and calls a `grant_trial` hook in `services/workspaces.py` that does nothing yet. BILL-002 creates the `credit_batches` row there and backfills a 20-credit trial batch for every workspace with `trial_granted_at` set and no batch. The "20 trial credits" criterion is met when BILL-002 lands.
- **WS-004 (member invites) isn't built**, but the `invites` table is. This task adds the accept side (`POST /invites/accept`), so join works the moment invites can be sent. Until then, the tests seed invites directly, and hand testing uses a one-line SQL insert (in the Log).
- **Getting started (DASH-002) and the app shell (DASH-001) come later.** Creating a workspace lands on app `/getting-started`, a placeholder with the workspace name until DASH-002. The workspace switcher itself is DASH-001; this task builds the switching logic it will call.
- **Default email templates (MSG-001)**: a no-op hook in the same create service, like the trial grant.

**API** (all under `/v1`, `VerifiedUserDep` on create and join so unverified accounts get `403 email_not_verified`)
- `POST /workspaces {name}` → in one transaction: workspace with a unique URL-safe slug from the name (lowercase ASCII, hyphens, ≤ 63; on a clash `-2`, `-3`…; a name with no usable letters gets `workspace`), owner membership (Admin, `is_owner`), `company_profiles` stub with `company_name = name`, `trial_granted_at = now()`, `profiles.last_workspace_id`. Returns the workspace in the `MyWorkspace` shape.
- `POST /invites/accept {code}` → checks pending, unexpired, addressed to the signed-in email (FR-AUTH-06); creates the membership with the invite's role and departments (or re-activates a removed one), marks the invite accepted, sets `last_workspace_id`. Errors: `404 invite_not_found`, `403 invite_wrong_email`, `410 invite_expired`, `410 invite_invalid` (revoked, or used by someone else). Already a member → returns the workspace (no error). `{token}` accept arrives with AUTH-004's link page.
- `PUT /me/last-workspace {workspace_id}` → remembers the active workspace across devices (FR-AUTH-04); not a member → 404.
- Codes are accepted as pasted: a bare code (`ab12-cd34`, any case, spaces trimmed) or a full `/join/AB12-CD34` link.
- API.md gains the last-workspace endpoint and the error codes; SECURITY.md notes invite-accept rate limiting waits for Redis (FND-008).

**Web** (`/workspaces` on the site host, frame WorkspaceSelect)
- Header with logo and an account menu (name, email, Log out; "User profile" arrives with AUTH-005). Eyebrow "Set up your workspace", heading "Welcome, {first name}. Where will you be hiring?", body, then the two cards: **Create a workspace** (name field, "Create workspace") and **Join a workspace** (invite link or code, "Join workspace"), "Signed in as {email} · Not you? Log out".
- A user who already has workspaces (for example, opening it to create a second one) also sees **Your workspaces** above the cards, each with role and member count; choosing one switches to it.
- Switching (`activateWorkspace` in `lib/workspaces/activate.ts`, wrapped by `useSwitchWorkspace` for DASH-001's switcher): set the `fh_ws` cookie, `PUT /me/last-workspace`, clear the TanStack Query cache, go to the app host.
- Join shows the API's errors inline in plain words (expired, revoked, different email with the masked address, not found). Create validates 1 to 120 characters.
- Mobile first: cards stack below `md`, two columns from `lg`; checked at 360, 768, 1024, 1440 px, Paper and Night. Copy in `messages/en.json`.

**Tests (after it works)**
- API integration: create (owner Admin, slug rules and clashes, company profile, `trial_granted_at`, last workspace), unverified → 403, accept (happy path with departments, expired, revoked, used, wrong email, already member, link-form code), last-workspace for another workspace → 404.
- API unit: slug and pasted-code rules. Web unit: error copy by code, name validation. Playwright: sign up → verify → create workspace → Getting started → open it from Choose workspace; unknown code shows its error.

**Board:** AUTH-001 Done, AUTH-002 Done, AUTH-003 In review.

## Log
- 2026-09-29: branch `feature/choose-workspace-5dvi3p`. The owner approved building this before BILL-002: creating a workspace sets `trial_granted_at`, and BILL-002 fills in `grant_trial()` and backfills the 20-credit batches.
- **Invite preview moved to AUTH-004.** The Join card calls `POST /invites/accept` directly and shows the error by code, so `GET /invites/{code}` is only needed by the `/join/[code]` page.
- **No audit entries.** SECURITY.md's audit list doesn't include creating or joining a workspace (inviting does, in WS-004), and `audit_log` rows can never be deleted, which would pin test workspaces.
- **Wrong email is checked first.** An invite addressed to someone else only ever says "different email", never whether it's expired or revoked. The error body carries no email (hard rule 8).
- **Already a member → success.** Accepting an invite to a workspace you're already in returns the workspace, so a double click or a second tab doesn't show an error. A removed member who is invited again gets their old membership row back with the invite's role.
- **`/workspaces` lists your workspaces** above the create and join cards when you have any, so it also works as "select". Signed-out visitors go to plain `/login` (not `?next=/workspaces`, because `next` is always an app-host path).
- **Switching** is `activateWorkspace()` (`lib/workspaces/activate.ts`): the `fh_ws` cookie plus `PUT /v1/me/last-workspace` (best effort; the cookie is enough on this device). `useSwitchWorkspace()` adds clearing the query cache, for DASH-001. From `/workspaces` the app opens with a full page load, so nothing is cached.
- **Slugs:** NFKD to ASCII, lowercase, runs of anything else become one hyphen, at most 56 characters so `-2`, `-3`… fit in 63; no letters or digits → `workspace`. A clash on insert (two creates at once) retries up to 3 times.
- Invite accept has no rate limit yet (needs Redis, FND-008); SECURITY.md notes it.
- Verified by hand with Chromium against local Supabase: create (empty name error, success → app `/getting-started` with the name), join with a full link in lowercase → app, wrong-email invite → message, sign-in with workspaces goes to the last one, `/workspaces` lists both workspaces with role and member count, account menu (sheet on phones) logs out; `fh_ws` and `last_workspace_id` both set. No horizontal scroll at 360, 768, 1024 and 1440 px, Paper and Night.
- Tests: `tests/integration/test_workspaces.py`, `tests/unit/test_workspace_rules.py`, `lib/workspaces/errors.test.ts`, `e2e/choose-workspace.spec.ts`.
