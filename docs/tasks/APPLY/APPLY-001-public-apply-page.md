# APPLY-001: Public apply page

| Field | Value |
|---|---|
| Epic | APPLY — Apply |
| Milestone | M3 Intake |
| Status | Done |
| Size | M |
| Depends on | [PIPE-001](../PIPE/PIPE-001-pipeline-model-and-state-machine.md), [WS-001](../WS/WS-001-company-profile.md), [FND-012](../FND/FND-012-ui-kit-design-system-components.md) |
| Requirements | FR-APPLY-01, FR-APPLY-06 |
| Gap areas | G2 |
| Design | Frame Apply |
| Docs to read | [`architecture/API.md (public)`](../../architecture/API.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Anyone with the apply link sees a clear, branded job page with the right status.

## Scope
**In:**
- `GET /public/pipelines/{ws}/{slug}` (candidate-safe fields only)
- Page sections as designed; mobile layout
- Status banners: accepting/closes, opens on, not taking applications, closed; 404 for draft/cancelled
- Source tag captured from URL and kept through sign-in

**Out:**
- Sign-in and form (APPLY-002/003)

## Acceptance criteria
- [x] Hidden fields (must-haves, skills, rubric) never returned by the public endpoint (test)
- [x] Lighthouse accessibility ≥ 95 (100, mobile)
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

Plan auto-approved (the owner's standing rule: no plan approvals).

**API**
- `GET /v1/public/pipelines/{workspace_slug}/{pipeline_slug}` (no sign-in) in `app/api/routers/public_pipelines.py`, schema `PublicPipeline` in `app/schemas/public_pipelines.py`.
- The read is a module function `public_pipeline_of()` in `repositories/pipelines.py`, like `branding_of()`: it selects only candidate-safe columns (id, slug, title, department name, employment type, work setup, location, JD, "Also open to", interview format, status, open and close dates) joined to the workspace (by slug) and its company profile (name, website, industry, size, HQ country, about, careers URL, logo). Must-haves, nice-to-haves, skills to probe, tone, seniority, weights, pass marks and credits are never selected.
- `draft`, `cancelled` and unknown slugs → `404 not_found`. A candidate-facing `availability` collapses the status: `accepting` (live), `opens_later` (scheduled), `not_accepting` (paused, paused_no_credits), `closed`.
- The logo is linked through the public branding route (`/v1/public/branding/{workspace_id}/logo?v=…`), so no Storage call and no expiring link. Dates are shown in the company profile's time zone, else the workspace's.

**Web**
- `/apply/[ws]/[pipeline]` on the site host (`app/site/apply/[ws]/[pipeline]/page.tsx`), a server component that fetches the endpoint uncached; `notFound()` on 404. Page title "{title} at {company}".
- Sections from frame Apply: branded header ("Hiring with FastHyr"), job header with status line, title, meta chips and Apply button, "About the role" with the JD, "Also open to" block, "How applying works" (step 3 follows the interview format), fairness note, "Role at a glance", About the company (website and careers links when set), footer.
- Mobile first: one column below `lg` (content, then role facts and the company card, in reading order), two columns (main + 400 px aside) from `lg`.
- JD is plain text: a pure `parseJobDescription()` in `lib/apply/` splits it into paragraphs, bullet lists (`-`, `*`, `•`, numbered) and short heading lines. No employer HTML is rendered.
- Status lines: "Accepting applications · closes {date}", "Opens on {date}", "Not taking applications right now", "This role is closed"; when not accepting, the Apply button is disabled with the reason (FR-APPLY-06).
- Source tag: `parseSource()` keeps only the known tags (`linkedin`, `jobstreet`, `indeed`, `kalibrr`, `glassdoor`, `facebook`, `careers`, `other`), else `direct`. The page keeps a valid tag in `sessionStorage` per pipeline (it survives the OAuth round trip in the same tab) and `applySource()` reads it back for APPLY-002/003.
- Apply now while accepting: sign-in is APPLY-002, so until then it opens a short dialog saying applying opens soon; APPLY-002 replaces it with the sign-in modal.

**Tests** (after hand testing): API integration test that the response has exactly the candidate-safe keys and none of the hidden fields, 404 for draft, cancelled, unknown slugs and another workspace's slug pair, and the availability mapping; web unit tests for `parseSource()` and `parseJobDescription()`; a Playwright spec that opens a seeded live pipeline's apply page.

## Log
_(Branch name, decisions, deviations, PR links, review files.)_

- 2026-10-02: branch `claude/apply-001-9yi4vy`.
- Decisions: on phones the role facts and company card follow the content (DOM order = reading order) rather than moving above it. The frame's Sign in button, signed-in menu and footer Privacy/Terms links are left out until APPLY-002 and WEB-005 build what they point to. Dates are formatted `en-GB` ("Fri, 26 Feb 2027") in the company profile's time zone because the page renders on the server. A friendly not-found page covers drafts, cancelled pipelines and bad links. "Also open to" reuses the wizard's option labels and descriptions. The seed gives Senior Backend Engineer a full job description so the page has realistic content locally.
- Follow-ups: rate limiting for public apply endpoints (SECURITY.md) has no shared limiter yet; add it with APPLY-003's write endpoints.
- Tested by hand at 360, 768, 1024 and 1440 px, light and dark, every availability state and the 404; Lighthouse accessibility 100.
