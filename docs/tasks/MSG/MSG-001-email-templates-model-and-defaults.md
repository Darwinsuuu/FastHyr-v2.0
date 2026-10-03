# MSG-001: Email templates model and defaults

| Field | Value |
|---|---|
| Epic | MSG — Candidate emails |
| Milestone | M3 Intake |
| Status | Done |
| Size | M |
| Depends on | [FND-010](../FND/FND-010-email-infrastructure-resend.md), [AUTH-003](../AUTH/AUTH-003-workspaces-create-join-by-code-select-switch.md) |
| Requirements | FR-MSG-01, FR-MSG-03 |
| Gap areas | G5 |
| Design | Frames EmailTemplates, EditEmailTemplate + A-07 |
| Docs to read | [`architecture/NOTIFICATIONS.md §1–3`](../../architecture/NOTIFICATIONS.md), [`design/VOICE_AND_TONE.md`](../../design/VOICE_AND_TONE.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Every workspace starts with warm, ready-to-use templates for each candidate email.

## Scope
**In:**
- `email_templates`, `email_template_versions` migrations
- Default template content for all 9 keys (written to VOICE_AND_TONE)
- Seeding on workspace creation; parameter validation; `[Review.link]` enforcement

**Out:**
- Editor UI (MSG-002)

## Acceptance criteria
- [x] New workspace has 9 templates
- [x] Unknown parameters rejected
- [x] Rejection templates always render the review line
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md)) (no screens in this task; the rendered emails were checked at 360 and 1440 px)
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Create the defaults for new workspaces in `create_default_email_templates()` (`app/services/workspaces.py`, called by `POST /workspaces` since AUTH-003), and backfill workspaces created before this task.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

1. **Tables** (migration `20261003150000_email_templates.sql`): `email_templates` and `email_template_versions` as in DATABASE.md. `key` is checked against the nine keys, unique per workspace; subject 1–200 characters, body up to 20,000. Versions reference their template by `(workspace_id, template_id)` and go with it. RLS on with no policies.
2. **Defaults** (`app/emails/defaults.py`): `TemplateKey`, the nine default subjects and bodies (the interview invitation is the canvas copy; the rest written to VOICE_AND_TONE), and `parameters_for(key)`: every template takes the candidate's names, job title and company name; only the three interview emails take `[Interview.link]` and `[Interview.expiry]`; only the two rejections take `[Review.link]`.
3. **Creating them** (`services/email_templates.py`): `ensure_defaults()` inserts any missing key (`on conflict do nothing`). `create_default_email_templates()` calls it when a workspace is created. Workspaces created before this task get theirs the first time `list_templates()` or `get_template()` reads them (no SQL copy of the wording to keep in step).
4. **Checks on save**: `validate()` collapses whitespace in the subject, cleans the body with the email allow-list, and refuses an empty or too long subject or message and any `[X.y]` the template can't fill (`422 email_template_invalid`, one `errors` entry per problem). `save()` stores the wording, clears `is_default`, sets `updated_by` and adds a version; MSG-002's editor calls it.
5. **Review line** (`app/emails/candidate.py`): `render_template()` adds "Want a person to review this decision? [Review.link]" to a rejection whose body doesn't have `[Review.link]`, turns link parameters in the text into links, and refuses to render when a parameter used has no value. MSG-003 sends through it.
6. **Seed**: Acme Talent gets the nine templates, with the interview invitation edited by Maria (the canvas's second wording).
7. **Tests**: unit (every default passes its checks and renders with no `[`; rejections always show the review line once; unknown and out-of-place parameters refused; cleaning; missing values); integration (a new workspace has nine; older workspaces get them on read, once; saves keep the history and stay in their workspace).

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
- 2026-10-03: branch `feature/msg-001-xrpo3d` from `develop`. Plan auto-approved (owner's standing rule). Marks MSG-001 Done on the board; MSG-002 and MSG-003 become Ready.
- Decisions (defaults picked, open to change): the default wording lives in code and each workspace keeps its own copy, so a later change to a default reaches new workspaces and "Reset to default" only. Older workspaces are backfilled when their templates are first read instead of by a SQL copy of the wording. `[Interview.link]`/`[Interview.expiry]` are refused outside the interview emails and `[Review.link]` outside rejections, because nothing could fill them. The review line goes after the sign-off, as the editor's locked footer line; when the editor keeps `[Review.link]` in the text, it isn't added twice.
- No endpoints in this task: the routes in API.md (`/email-templates…`) come with MSG-002's editor, with their tenancy tests.
- Hand-tested on local Supabase: `POST /v1/workspaces` gave the new workspace the nine default templates; a workspace inserted without them got all nine on first read and none on the second; saving `[Candidate.first_name]`, `[Interview.link]` in a rejection or `[Foo.bar]` was refused with one error each while `[sic]` stayed text; a rejection saved without the review line was sent to Mailpit with it, and scripts and event attributes were stripped on save. Screenshots of the rendered invitation and rejections at 360 and 1440 px were attached to the PR thread.
