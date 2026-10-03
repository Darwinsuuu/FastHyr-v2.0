-- MSG-003 Email scheduling and sending engine: candidate emails remember the application stage
-- they were written for, so one whose application has moved on is cancelled instead of sent
-- (FR-MSG-05); a dedupe key keeps a retried job from scheduling the same email twice; a hard
-- bounce marks the candidate's address undeliverable. Design: docs/architecture/
-- NOTIFICATIONS.md §1 and §5, DATABASE.md (Messaging, Candidates).

-- Null for emails that aren't about an application (invites, tests).
alter table public.email_messages add column application_stage text;
-- Set by the scheduling service, e.g. 'reject_resume:{application_id}:resume_not_match'.
alter table public.email_messages add column dedupe_key text;

-- One live email per key; a cancelled email frees its key so it can be scheduled again.
create unique index email_messages_dedupe_key_key
  on public.email_messages (dedupe_key)
  where dedupe_key is not null and status <> 'cancelled';

-- Set by a hard bounce while the candidate still has that address; cleared when they apply again
-- with a different one. Shown on the candidate profile.
alter table public.candidates add column email_undeliverable_at timestamptz;
