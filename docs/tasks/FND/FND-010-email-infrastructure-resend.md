# FND-010: Email infrastructure (Resend)

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | In review |
| Size | M |
| Depends on | [FND-008](../FND/FND-008-background-worker-and-job-framework.md) |
| Requirements | FR-MSG-04, FR-MSG-06 |
| Gap areas | G5 |
| Design | — |
| Docs to read | [`architecture/NOTIFICATIONS.md`](../../architecture/NOTIFICATIONS.md), [`decisions/ADR-008-resend-for-email.md`](../../decisions/ADR-008-resend-for-email.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
The API can render a branded email, log it and send it through Resend, with delivery status coming back by webhook.

## Scope
**In:**
- `email_messages` migration
- `services/emails.py`: render (Jinja2 layout + sanitised body + params), schedule, send job
- Resend client wrapper + webhook endpoint with signature check
- Dev mode: log/preview emails instead of sending

**Out:**
- Workspace templates (MSG-001)
- Business-day scheduling (MSG-003)

## Acceptance criteria
- [ ] System email (e.g. test) sends on the development environment and status updates to delivered
- [x] HTML sanitised with allow-list
- [x] Plain-text alternative generated
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Sender name `{Company} via FastHyr`
- Member invite email: fill in `services/invites.send_invite_email(invite, token)` (WS-004 calls it on invite and resend; link `/join/<code>` plus the code, 7-day expiry). Then change the invite dialog copy in `messages/en.json` (`members.invites.inviteDialog.body`, `shareDialog`) to say the email was sent, as the ManageMembers frame does.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Unit tests for rendering and sanitising

## Implementation plan
**Schema**: `email_messages` as in DATABASE.md, plus `from_name`, `html_rendered`, `text_rendered` (rendered when queued, so a send never re-renders), `status_updated_at`, `created_at`, a `complained` status and a unique `provider_message_id`. `workspace_id` is nullable for the contact form. RLS on, no policies.

**Rendering** (`app/emails/`): `render.render()` fills `[Name.field]` parameters (values HTML-escaped), cleans the body with an `nh3` allow-list (p, br, strong, em, a[href], ul, li; http/https/mailto links get `rel="noopener noreferrer"`), wraps it in the Jinja2 layout (brand colours of the Supabase auth templates; company emails get "Sent by {Company} via FastHyr · Why am I getting this? · Privacy") and builds the plain-text part from the HTML. `system.py` builds the member invite and test emails.

**Sending** (`services/emails.py`, `jobs/emails.py`, `integrations/email.py`): `queue_email()` in the caller's transaction, `enqueue()` after commit (deferred to `scheduled_for`). The `send_email` job claims the row, sends, records the provider ID. Outages retry 5 times with backoff; a rejection fails at once (`PermanentJobError`, new in the framework). Resend gets the row ID as `Idempotency-Key`. Backends: Resend when `RESEND_API_KEY` is set; locally SMTP to Mailpit (Supabase's `[local_smtp] smtp_port = 54325` turned on); otherwise log the ID only. The sweeper re-queues due emails still scheduled after 10 minutes. `JobQueue.enqueue` now returns False instead of raising when Redis is unreachable, so the request still succeeds and the sweeper sends it later.

**Webhook**: `POST /v1/webhooks/resend` checks the Svix signature (`RESEND_WEBHOOK_SECRET`, 5-minute tolerance) and maps delivered, bounced, complained and failed onto the row by provider ID, never undoing a bounce or complaint.

**Invites**: `services/invites.queue_invite_email()` replaces the WS-004 stub; create and resend queue it in the invite's transaction. The link is `{SITE_URL}/join/{token}` plus the code. Invite dialog copy now says the email was sent (frame ManageMembers); the share dialog stays as a backup with the code.

**Dev**: `POST /v1/dev/test-email` (local and development) sends the test email to yourself.

**Tests**: unit tests for the allow-list, parameter escaping, plain text, the invite email and webhook signatures; integration tests that run the worker with a fake sender (invite email sent, outage retried, rejection fails once, sweeper re-queue, signed webhooks move the status and a bad signature is refused); the member invites e2e journey checks the email reaches Mailpit with a `/join/` link.

## Log
- 2026-10-01: branch `feature/email-infrastructure`, built on FND-008 (PR #20). Plan auto-approved (Darwin's standing rule: no plan approvals).
- Decision: system emails other than company ones come from "FastHyr" (the invite names the workspace in the subject and body). Company emails use "{Company} via FastHyr" (ADR-008).
- Decision: the rendered subject, HTML and text are stored on the row, so what was sent is exactly what is logged and a retry can't render differently.
- Hand test (local Supabase, Redis, worker): `POST /v1/dev/test-email` and `POST /v1/invites` both arrived in Mailpit (from "Hand test via FastHyr" and "FastHyr"), rows went scheduled → sent; signed `email.delivered` then `email.bounced` webhooks moved the test email to delivered then bounced; a bad signature got `400 invalid_webhook_signature`. Screenshots of both emails at 360 and 1440 and of the invite dialogs: project files `screenshots/FND-010/`.
- Open: the first acceptance criterion (send on the development environment, status reaches delivered) needs a Resend API key and webhook secret on the development environment, which comes with FND-007. Locally the same path is verified with Mailpit and a signed webhook.
