# ADR-008: Resend for transactional email

- **Status:** Accepted
- **Date:** 2026-09-29

## Decision
- All emails (candidate emails from templates, invites, password reset from Supabase via custom SMTP, contact form notifications, receipts are Stripe's) are sent through **Resend**.
- Sending domain: `mail.fasthyr.com` (SPF, DKIM, DMARC set up). From address: `no-reply@fasthyr.com`; candidate emails show the employer's company name as the sender name ("Acme Talent via FastHyr").
- Supabase Auth emails use Resend as custom SMTP so all mail shares one domain reputation.
- Every send is logged in `email_messages` with Resend's message ID; Resend webhooks update delivery status (delivered, bounced, complained).

## Consequences
- Templates are rendered by the API (Jinja2 layout + sanitised user-edited HTML), not by Resend.
