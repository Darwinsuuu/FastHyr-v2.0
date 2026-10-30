# MSG-002: Email templates list and editor

| Field | Value |
|---|---|
| Epic | MSG — Candidate emails |
| Milestone | M3 Intake |
| Status | Done |
| Size | M |
| Depends on | [MSG-001](../MSG/MSG-001-email-templates-model-and-defaults.md), [DASH-001](../DASH/DASH-001-app-shell.md) |
| Requirements | FR-MSG-02 |
| Gap areas | G5 |
| Design | Frames EmailTemplates, EditEmailTemplate + A-07 |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users adjust the wording of every candidate email, test it and restore earlier versions.

## Scope
**In:**
- List with filters and edited-by info
- Tiptap editor (bold, italic, link, bullets, parameter chips), subject
- Reset to default, version history view/restore, send test to me

**Out:**
- —

## Acceptance criteria
- [x] Saved HTML sanitised
- [x] Restore creates a new version
- [x] Admins and Recruiters only
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
1. **API** (`app/api/routers/email_templates.py`, `require(MANAGE_EMAIL_TEMPLATES)`): the API.md routes. `GET /v1/email-templates` (the ten, with `is_default`, `updated_at` and `updated_by {id, name}`), `GET/PUT /{key}` (detail adds `body_html`, the template's `parameters` and `review_line`), `POST /{key}/reset`, `GET /{key}/versions` (newest first, each with `kind` edit/reset/restore and who), `POST /{key}/versions/{version_id}/restore`, `POST /{key}/test`. An unknown key or a version of another template or workspace is `404 not_found`.
2. **Service** (`services/email_templates.py`): saves keep going through MSG-001's `save()` (allow-list clean, `422 email_template_invalid`, a version row), which now records the kind in `email_template_versions.note` and sets `is_default` when the wording equals FastHyr's default (so a reset shows "Using the default template" again). Reset saves the default and restore saves the old version's wording, both as new versions; history is never rewritten. Each change writes an audit row (`email_template.edited|reset|restored`, key and version only).
3. **Send test to me**: renders the editor's wording (saved or not) with `render_template()` and the sample candidate (Bea Garcia · Senior Backend Engineer · the workspace's company), sample interview and review links, the workspace's branding and the review line on rejections, and queues it to the caller's own address (`template_key = test`).
4. **Web**: `/settings/email-templates` (`EmailTemplatesPage`) cards with category label, description, subject, timing and "Edited {date} by {name}" or "Using the default template", filter chips (All, Invitations, Reminders, Advancement, Rejections, Updates; confirmations sit with Updates); `/settings/email-templates/[key]` (`TemplateEditorPage`) with a Tiptap editor (`RichTextEditor`: StarterKit cut to bold, italic, link, bullets, plus an atom `parameter` node), parameter panel and Insert parameter menu, the locked review line on rejections, client checks that mirror the API, Reset dialog, Change history with view/restore, and the test dialog. Logic in `lib/email-templates`.
5. **Tests**: integration tests for edit/reset/restore/history/audit, refusals and the test email; tenancy registry entries (`Case.fixed` for the key in the path); vitest for the lib; Playwright `e2e/email-templates.spec.ts`.

## Log
- 2026-10-30: Branch `feature/email-templates-editor` from `develop`. Plan auto-approved (owner's standing rule). Marks MSG-002 Done on the board; nothing new becomes Ready (DASH-002 also waits on BILL-004).
- `[Review.link]` isn't offered in the insert lists: every rejection gets the review line anyway, shown locked under the message (A-07). If a body already has it, the locked line is hidden, as rendering doesn't add it twice.
- The "Interview received" card is labelled Confirmation (A-07) and filed under the Updates filter, since A-07 only adds "Updates".
- Copy for the four templates the frame doesn't show (Interview received, Role closed, Human review received, Review outcome) follows A-07's timing text and VOICE_AND_TONE.md.
- Save returns to the list as in the frame; the test email sends the wording on screen, saved or not, so it can be tried before saving. Leaving the page with unsaved changes asks the browser's "leave site?" question.
- History wording ("edited the message", "changed the subject line", "reset the template to default", "restored an earlier version") is worked out by comparing each version with the one before it.
- Seed: Acme Talent's invitation, résumé rejection and next-stage templates now have a short change history (Dana and Maria) dated in the past.
- Also added the "Edit templates" link PIPE-003 left out of the wizard's Candidate messages card (opens in a new tab so the wizard keeps its steps).
- New web dependency: Tiptap 3.32.0 (`@tiptap/core`, `@tiptap/pm`, `@tiptap/react`, `@tiptap/starter-kit`), as FR-MSG-02 and the task scope name it.
