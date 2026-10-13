# ASMT-008: Human review requests

| Field | Value |
|---|---|
| Epic | ASMT — Assessment & review |
| Milestone | M5 Review |
| Status | Done |
| Size | M |
| Depends on | [ASMT-007](../ASMT/ASMT-007-advance-and-reject-actions.md), [SCREEN-003](../SCREEN/SCREEN-003-post-screen-actions-invite-or-schedule-rejection.md) |
| Requirements | FR-COMP-03 |
| Gap areas | G2, G5 |
| Design | S-03 + A-03 |
| Docs to read | [`decisions/ADR-015-automated-decisions-human-review.md`](../../decisions/ADR-015-automated-decisions-human-review.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Candidates can ask a person to review an automated rejection, and TA teams resolve it.

## Scope
**In:**
- `human_review_requests` migration (requests point at the `review_links` row SCREEN-003 created with the rejection email; look the token up by hash there)
- `/review-request/[token]` page
- Owner notification + candidate acknowledgement emails
- Filter/badge/banner and resolve actions (uphold/override)

**Out:**
- —

## Acceptance criteria
- [x] Override re-enters the correct stage and sends the right email
- [x] Link valid 30 days
- [x] All resolutions audited
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- A TA's own rejection (ASMT-007) also carries a review link (`decision_type` by whether the interview was finished), and Rejected is final: decide whether a request on it can override, or only be answered.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Plan auto-approved per the owner's standing rule; see Log.)_

1. **Migration `20261013090000_human_review_requests.sql`** (expand-only): `human_review_requests` with the DATABASE.md columns (`decision_type`, `review_link_id` FK to `review_links`, `candidate_message` ≤ 1,000, `status open|upheld|overridden`, `resolved_by` member ID, `resolved_at`, `resolution_note`, `created_at`), deleted with the application; at most one open request per application (partial unique index); `review_links.requested_at` marks a link already used (a TA rejection that gives the link a new token clears it, so a new decision can be reviewed again). RLS on, no policies.
2. **Public API** (`services/review_requests.py`, `routers/public_review_requests.py`): `GET /v1/public/review-requests/{token}` returns `state` (`open`, `requested`, `expired`, `unavailable`), company and job title only; `POST` with an optional message creates the request in one transaction: request row, `applications.review_requested`, `review_links.requested_at`, the candidate's `review_received` email (sent now) and the owner email (system email `review_request` to the pipeline owner, or the workspace's Admins when the pipeline has no owner), audit `review_request.created`. A repeat POST returns `requested`; an expired link or an application that moved on is `409 review_link_closed`. Unknown tokens are `404`. The link works until `review_links.expires_at` (30 days after its email).
3. **Team API** (`routers/review_requests.py`, `RESOLVE_REVIEWS`, department scope, else `404`): `GET /v1/review-requests?status=open` lists requests; `POST /v1/review-requests/{id}/resolve {outcome: uphold|override, note}` (note required, 1,000 characters). Uphold: `upheld`, overlay cleared, no email. Override: résumé decision in `resume_not_match` → `invited` with a new interview link and the invitation (the fallback skills plan is stored first when the failed screen has none); interview decision in `did_not_pass` → `ready_for_review`, no email. A request on a TA's own rejection (stage `rejected`) can only be upheld (`409 override_not_allowed`), so Rejected stays final. A resolved request is `409 review_request_resolved`. Audit `review_request.resolved` with outcome and stages, never the note or message.
4. **Profile**: `GET /v1/applications/{id}` adds `review_request` (open request: id, decision type, message, time, whether it can be overridden) and journey steps for requested and resolved reviews (who, outcome, note). Overview `attention.review_requests` (count, for DASH-004).
5. **Web**: `/review-request/[token]` on the site host (S-03 card in the interview link layout: open with the optional textarea and "Request a review", sent, already requested, expired with the company's website); A-03 banner on top of the profile's Overview (the Résumé tab comes with ASMT-005) with the quote and "Uphold decision" / "Invite to interview" or "Move to Ready for review", each opening a dialog that requires a note; read only for Hiring managers. The Candidates tab filter and badge exist from PIPE-008.
6. **Seed**: two open review requests in Acme Talent (one résumé, one interview).
7. **Tests**: request + resolve service tests (both overrides, uphold, TA rejection, expired, repeat), the public page states, tenancy for the new endpoints; web unit tests for the page states helper.

## Log
- 2026-10-13: branch `feature/asmt-008-0t4xw9`. Plan written above and auto-approved under the owner's standing rule (no plan approvals).
- Decision (default picked, asked on a card): a request about a person's own rejection (ASMT-007, stage `rejected`) can only be upheld, so Rejected stays final.
- Defaults picked: upholding sends no email (SCREEN_SPECS.md A-03; the rejection already went out); the owner email goes to the Admins when the pipeline has no active owner; overriding a résumé decision stores the fallback skills plan (no model call in the request) because failed screens have none; the banner sits on Overview for both kinds until ASMT-005 builds the Résumé tab; the public endpoints have no rate limit yet (none of the public endpoints do).
- New API setting `APP_URL` (the app host, for the profile link in the owner email), set in `render.yaml` for dev and QA.
- Hand test (2026-10-13, local seed): requested, repeated and expired links through the API and the page; override résumé (Joshua Lim → Invited, invitation in Mailpit), override interview from the profile (Sofia Tan → Ready for review, journey shows who and the note), uphold, note required, 360/768/1024/1440 px, light and dark. Screenshots in `screenshots/ASMT-008/` of the project files.
