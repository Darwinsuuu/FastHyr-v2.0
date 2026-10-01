-- FND-010 Email infrastructure: every email the API sends is one email_messages row, rendered
-- when it is queued and sent by the send_email job through Resend. Resend webhooks move it to
-- delivered, bounced or complained. Design: docs/architecture/NOTIFICATIONS.md, DATABASE.md.

create table public.email_messages (
  id uuid primary key default gen_random_uuid(),
  -- Null only for emails that belong to no workspace (the public contact form).
  workspace_id uuid references public.workspaces (id),
  -- Candidate emails; the foreign key to applications comes with APPLY-003.
  application_id uuid,
  -- Workspace template keys (MSG-001) or system email keys such as member_invite and test.
  template_key text not null,
  to_email text not null,
  from_name text not null,
  subject_rendered text not null,
  html_rendered text not null,
  text_rendered text not null,
  scheduled_for timestamptz not null default now(),
  status text not null default 'scheduled' check (
    status in (
      'scheduled', 'cancelled', 'sending', 'sent', 'delivered', 'bounced', 'complained', 'failed'
    )
  ),
  provider_message_id text,
  cancel_reason text,
  sent_at timestamptz,
  status_updated_at timestamptz not null default now(),
  -- A stable error code, never a provider message that could repeat the address.
  error text,
  created_at timestamptz not null default now()
);

create index email_messages_workspace_id_created_at_idx
  on public.email_messages (workspace_id, created_at);
create index email_messages_application_id_idx
  on public.email_messages (application_id) where application_id is not null;
create unique index email_messages_provider_message_id_key
  on public.email_messages (provider_message_id) where provider_message_id is not null;
-- The requeue_stuck_work sweeper looks for due emails that were never sent.
create index email_messages_scheduled_for_idx
  on public.email_messages (scheduled_for) where status = 'scheduled';

-- Lockdown: RLS on with no policies; no privileges for the public keys.
alter table public.email_messages enable row level security;
revoke all on public.email_messages from anon, authenticated;
