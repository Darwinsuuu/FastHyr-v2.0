# Email and notifications

Provider: Resend (ADR-008). All emails go through `services/emails.py`, which renders, logs (`email_messages`) and enqueues `send_email`.

## 1. Candidate emails (workspace templates, editable)
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
Unknown parameters are rejected on save. Rendering escapes values; the body HTML is sanitised with an allow-list (p, br, strong, em, a[href], ul, li).

## 3. Layout
Jinja2 layout: company banner (or logo), body, footer ("Sent by {Company} via FastHyr · Why am I getting this? · Privacy"). Plain-text alternative generated from HTML. From: `"{Company} via FastHyr" <no-reply@fasthyr.com>`, Reply-To: none in MVP (post-MVP: company reply address).

## 4. System emails (not editable)
| Email | Trigger |
|---|---|
| Member invite | Admin invites (link + code, expires in 7 days) |
| Password reset / email verification | Supabase Auth via Resend SMTP (branded templates in Supabase config) |
| Human review request to TA | Candidate requests review → pipeline owner |
| Pipeline paused (out of credits) / running low | Credits service → pipeline owner + Admins |
| Payment failed | Stripe webhook → Admins |
| Contact form | → hello@fasthyr.com |
| Test email | "Send test to me" in template editor (sample data: Bea Garcia · Senior Backend Engineer · workspace name) |

## 5. Deliverability and logging
- `mail.fasthyr.com` with SPF, DKIM, DMARC (p=quarantine after warm-up).
- Resend webhooks update `email_messages.status`; hard bounces mark the candidate email as undeliverable (shown on the profile).
- No tracking pixels or link tracking on candidate emails (privacy).

## 6. In-app notifications
None in MVP — the Overview "Needs your attention" list is the notification surface.
