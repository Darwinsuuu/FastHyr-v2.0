# Email and notifications

Provider: Resend (ADR-008). All emails go through `services/emails.py`, which renders, logs (`email_messages`) and enqueues `send_email`.

How it works (FND-010):
- **Render** with `app/emails/render.render()`: parameters filled (values HTML-escaped), body cleaned with the allow-list (`nh3`), Jinja2 layout `app/emails/templates/layout.html.jinja`, plain-text alternative generated from the HTML. System emails are built in `app/emails/system.py`.
- **Queue** with `emails.queue_email()` in the same transaction as the change that causes the email, commit, then `emails.enqueue()`. The `send_email` job claims the row (`scheduled` → `sending`), sends it, and records the provider ID (`sent`). Provider outages retry 5 times with backoff; a rejected email fails at once (`provider_rejected`). Resend's `Idempotency-Key` is the row ID, so a retried send is never delivered twice. `requeue_stuck_work` re-queues due emails still `scheduled` after 10 minutes.
- **Providers** (`app/integrations/email.py`, `EMAIL_BACKEND=auto`): Resend when `RESEND_API_KEY` is set; locally, local Supabase's Mailpit over SMTP (port 54325, read at http://127.0.0.1:54324); elsewhere without a key, log the message ID only.

## 1. Candidate emails (workspace templates, editable)

Templates (MSG-001): each workspace has one `email_templates` row per key, made from FastHyr's defaults in `app/emails/defaults.py` when the workspace is created (older workspaces get them the first time `services/email_templates.py` reads them). Saves go through `email_templates.save()`, which checks parameters, cleans the body and adds an `email_template_versions` row. Candidate emails are rendered with `app/emails/candidate.render_template()`, which adds the review line to rejections, makes link parameters clickable and refuses to render a parameter that has no value.

| Key | Name (UI) | Trigger | Timing | Controlled by |
|---|---|---|---|---|
| `interview_invitation` | Interview invitation | Résumé passes, or manual invite / override | Immediately | always |
| `interview_reminder` | Interview reminder | Link not started | 24 h before expiry | pipeline "Remind candidates" toggle |
| `finish_interview` | Finish your interview | Attempt abandoned, link still valid | 1 h after abandonment (once) | always |
| `interview_received` | Interview received *(new)* | Interview completed | Immediately | pipeline "Email candidates after their interview" |
| `next_stage` | Moving to the next stage | TA clicks Advance (ADR-017) | Immediately | TA can untick in the Advance dialog |
| `reject_resume` | Not moving forward — résumé | Stage `resume_not_match` | 2 business days after screening | pipeline "Email candidates whose résumé isn't a match" |
| `reject_interview` | Not moving forward — interview | Stage `did_not_pass`, or TA Reject after interview | `did_not_pass`: 3 business days after interview; TA reject: immediately | pipeline toggle / Reject dialog checkbox |
| `role_closed` | Role closed *(new)* | Pipeline closed with "let candidates know" ticked | Immediately, to candidates with no final outcome email | Close dialog |
| `review_received` | Human review received *(new)* | Candidate submits a review request | Immediately | always |

When a TA rejects a candidate who has not finished an interview, the email uses `reject_resume`; after a finished interview it uses `reject_interview`.

Business days skip Saturday/Sunday in the workspace time zone (public holidays: post-MVP). Scheduled emails are cancelled when the application's stage changes before send time (FR-MSG-05).

## 2. Parameters
`[Candidate.firstname]`, `[Candidate.lastname]`, `[Job.title]`, `[Company.name]`, `[Interview.link]`, `[Interview.expiry]` (formatted in the workspace time zone, e.g. "Fri, 3 Oct 2026, 11:59 PM PHT"), `[Review.link]` (rejection templates only; auto-appended as a footer line if the editor removed it — ADR-015).
Only the three interview emails (`interview_invitation`, `interview_reminder`, `finish_interview`) take `[Interview.link]` and `[Interview.expiry]`, since no other email has an interview link to fill.
Unknown parameters are rejected on save (`422 email_template_invalid`, one `errors` entry per parameter). Rendering escapes values; the body HTML is sanitised with an allow-list (p, br, strong, em, a[href], ul, li).

## 3. Layout
Jinja2 layout: company banner (or logo), body, footer ("Sent by {Company} via FastHyr · Why am I getting this? · Privacy"). Plain-text alternative generated from HTML. From: `"{Company} via FastHyr" <no-reply@fasthyr.com>`, Reply-To: none in MVP (post-MVP: company reply address).

## 4. System emails (not editable)
| Email | Trigger |
|---|---|
| Member invite | Admin invites or resends (link `{site}/join/{token}` + code, expires in 7 days); from "FastHyr" (FND-010) |
| Password reset / email verification | Supabase Auth via Resend SMTP (branded templates in Supabase config) |
| Human review request to TA | Candidate requests review → pipeline owner |
| Pipeline paused (out of credits) / running low | Credits service → pipeline owner + Admins |
| Payment failed | Stripe webhook → Admins |
| Contact form | → hello@fasthyr.com |
| Test email | "Send test to me" in template editor (sample data: Bea Garcia · Senior Backend Engineer · workspace name); a plain system test is `POST /v1/dev/test-email` (local and development) |

## 5. Deliverability and logging
- `mail.fasthyr.com` with SPF, DKIM, DMARC (p=quarantine after warm-up).
- Resend webhooks update `email_messages.status`; hard bounces mark the candidate email as undeliverable (shown on the profile).
- No tracking pixels or link tracking on candidate emails (privacy).

## 6. In-app notifications
None in MVP — the Overview "Needs your attention" list is the notification surface.
