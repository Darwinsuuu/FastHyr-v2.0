-- MSG-001 Email templates model and defaults: each workspace's editable candidate emails, one
-- row per template key, and every saved version of them. Design: docs/architecture/
-- NOTIFICATIONS.md §1-3 and DATABASE.md (Messaging). Only apps/api/app/services/
-- email_templates.py writes these rows. The default wording lives in apps/api/app/emails/
-- defaults.py: new workspaces get it when they are created, and workspaces created before this
-- task get it the first time their templates are read.

create table public.email_templates (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  key text not null check (
    key in (
      'interview_invitation', 'interview_reminder', 'finish_interview', 'interview_received',
      'next_stage', 'reject_resume', 'reject_interview', 'role_closed', 'review_received'
    )
  ),
  subject text not null check (length(btrim(subject)) between 1 and 200),
  -- Sanitised HTML (p, br, strong, em, a[href], ul, li) with [Name.field] parameters. Rejection
  -- templates may leave out [Review.link]: the review line is added when the email is rendered.
  body_html text not null check (length(btrim(body_html)) between 1 and 20000),
  -- True until someone saves their own wording; "Reset to default" sets it again.
  is_default boolean not null default true,
  -- Null while the template is FastHyr's default.
  updated_by uuid references public.profiles (id),
  updated_at timestamptz not null default now(),
  constraint email_templates_workspace_id_key_key unique (workspace_id, key),
  constraint email_templates_workspace_id_id_key unique (workspace_id, id)
);

create trigger email_templates_set_updated_at
  before update on public.email_templates
  for each row execute function public.set_updated_at();

-- Change history (FR-MSG-02): one row per save, reset or restore, newest last.
create table public.email_template_versions (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  template_id uuid not null,
  subject text not null,
  body_html text not null,
  created_by uuid references public.profiles (id),
  created_at timestamptz not null default now(),
  -- e.g. "Reset to default", "Restored the version from 20 Sep 2026".
  note text,
  constraint email_template_versions_template_fkey foreign key (workspace_id, template_id)
    references public.email_templates (workspace_id, id) on delete cascade
);

create index email_template_versions_template_id_created_at_idx
  on public.email_template_versions (template_id, created_at);

-- Lockdown: RLS on with no policies; no privileges for the public keys.
alter table public.email_templates enable row level security;
alter table public.email_template_versions enable row level security;

revoke all on public.email_templates from anon, authenticated;
revoke all on public.email_template_versions from anon, authenticated;
