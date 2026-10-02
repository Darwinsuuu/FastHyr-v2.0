-- PIPE-001 Pipeline model and state machine: the setup, schedule and lifecycle columns of
-- pipelines, and the trigger that locks the setup once a pipeline opens.
-- Design: docs/product/WORKFLOW.md §2 and docs/architecture/DATABASE.md (pipelines).
-- BILL-002 created the table with the credit columns; WS-002 added department_id.
--
-- Setup columns are nullable: a draft can be saved at any wizard step, and publishing checks
-- that the setup is complete (services/pipelines.py).

alter table public.pipelines
  -- The member who created it, and who published it.
  add column owner_id uuid,
  add column published_by uuid,
  add column slug text,
  -- Role
  add column title text,
  add column employment_type text,
  add column work_setup text,
  add column location text,
  add column jd_text text,
  add column must_haves text[] not null default '{}',
  add column nice_to_haves text[] not null default '{}',
  add column open_to text[] not null default '{}',
  add column resume_pass_bar integer not null default 60,
  -- AI interview
  add column interview_format text,
  add column tone text,
  add column seniority text,
  add column skills_to_probe text[] not null default '{}',
  add column link_expiry_days integer not null default 5,
  add column reminder_enabled boolean not null default true,
  add column integrity_enabled boolean not null default true,
  -- Scoring
  add column weight_technical integer,
  add column weight_communication integer,
  add column weight_culture integer,
  add column pass_mark integer not null default 70,
  add column email_resume_reject boolean not null default true,
  add column email_post_interview boolean not null default true,
  -- Schedule & credits. credits_to_reserve is what the wizard asks to reserve, kept on the
  -- draft; publishing reserves it through the credit service (credits_reserved).
  add column open_mode text,
  add column opens_at timestamptz,
  add column duration_days integer,
  add column closes_at timestamptz,
  add column credits_to_reserve integer,
  -- Lifecycle
  add column closed_reason text,
  add column archived_at timestamptz,
  add column published_at timestamptz,
  add column locked_at timestamptz,
  add column duplicated_from_id uuid,

  add constraint pipelines_owner_fkey foreign key (workspace_id, owner_id)
    references public.workspace_members (workspace_id, id),
  add constraint pipelines_published_by_fkey foreign key (workspace_id, published_by)
    references public.workspace_members (workspace_id, id),
  add constraint pipelines_duplicated_from_fkey foreign key (workspace_id, duplicated_from_id)
    references public.pipelines (workspace_id, id),

  add constraint pipelines_employment_type_check check (
    employment_type in ('full_time', 'part_time', 'contract', 'internship')
  ),
  add constraint pipelines_work_setup_check check (work_setup in ('on_site', 'hybrid', 'remote')),
  add constraint pipelines_open_to_check check (
    open_to <@ array[
      'fresh_grads', 'career_changers', 'returners', 'no_degree', 'step_up', 'relocating'
    ]::text[]
  ),
  add constraint pipelines_resume_pass_bar_check check (resume_pass_bar between 0 and 100),
  add constraint pipelines_interview_format_check check (
    interview_format in ('video_voice', 'voice_only')
  ),
  add constraint pipelines_tone_check check (tone in ('warm', 'professional', 'direct')),
  add constraint pipelines_seniority_check check (seniority in ('entry', 'mid', 'senior', 'lead')),
  add constraint pipelines_link_expiry_days_check check (link_expiry_days in (3, 5, 7, 14)),
  add constraint pipelines_weights_check check (
    weight_technical between 0 and 100
    and weight_communication between 0 and 100
    and weight_culture between 0 and 100
    and weight_technical + weight_communication + weight_culture = 100
  ),
  add constraint pipelines_pass_mark_check check (pass_mark between 0 and 100),
  add constraint pipelines_open_mode_check check (open_mode in ('now', 'scheduled')),
  add constraint pipelines_duration_days_check check (duration_days in (30, 60, 90, 120)),
  add constraint pipelines_credits_to_reserve_check check (
    credits_to_reserve >= 10 and credits_to_reserve % 10 = 0
  ),
  add constraint pipelines_closed_reason_check check (
    closed_reason in ('schedule', 'manual') and (status = 'closed') = (closed_reason is not null)
  ),
  add constraint pipelines_archived_check check (
    archived_at is null or status in ('closed', 'cancelled')
  ),
  -- Published pipelines have an apply link; drafts don't yet.
  add constraint pipelines_published_check check (
    (status = 'draft') = (published_at is null) and (published_at is null) = (slug is null)
  );

-- Existing rows are test or seed data from before this task (BILL-002, FND-014). Give the ones
-- already past draft the published fields the new checks expect.
update public.pipelines
set
  published_at = created_at,
  slug = 'pipeline-' || left(id::text, 8),
  closed_reason = case when status = 'closed' then 'manual' end,
  locked_at = case when status not in ('scheduled', 'cancelled') then created_at end
where status <> 'draft';

create index pipelines_workspace_id_status_idx on public.pipelines (workspace_id, status);
create unique index pipelines_workspace_id_slug_key on public.pipelines (workspace_id, slug);
-- For the every-minute cron that opens and closes pipelines.
create index pipelines_opens_at_idx on public.pipelines (opens_at) where status = 'scheduled';
create index pipelines_closes_at_idx on public.pipelines (closes_at)
  where status in ('live', 'paused', 'paused_no_credits');

-- ---------------------------------------------------------------------------
-- Lock: from the moment a pipeline is live (locked_at set) its Role, AI interview, Scoring and
-- Schedule sections can't change (WORKFLOW.md §2). Only status, credits and lifecycle columns
-- move. department_id may still become null: deleting a department moves its pipelines to
-- No department (WS-002). The slug never changes once published (FR-PIPE-15).
-- ---------------------------------------------------------------------------
create function public.pipelines_lock_setup() returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if old.published_at is not null and new.slug is distinct from old.slug then
    raise exception 'pipeline slug is fixed after publish' using errcode = 'P0001',
      hint = 'pipeline_locked';
  end if;
  if old.locked_at is null then
    return new;
  end if;
  if new.locked_at is distinct from old.locked_at
    or (new.department_id is distinct from old.department_id and new.department_id is not null)
    or (
      new.title, new.employment_type, new.work_setup, new.location, new.jd_text, new.must_haves,
      new.nice_to_haves, new.open_to, new.resume_pass_bar, new.interview_format, new.tone,
      new.seniority, new.skills_to_probe, new.link_expiry_days, new.reminder_enabled,
      new.integrity_enabled, new.weight_technical, new.weight_communication, new.weight_culture,
      new.pass_mark, new.email_resume_reject, new.email_post_interview, new.open_mode,
      new.opens_at, new.duration_days, new.closes_at, new.credits_to_reserve
    ) is distinct from (
      old.title, old.employment_type, old.work_setup, old.location, old.jd_text, old.must_haves,
      old.nice_to_haves, old.open_to, old.resume_pass_bar, old.interview_format, old.tone,
      old.seniority, old.skills_to_probe, old.link_expiry_days, old.reminder_enabled,
      old.integrity_enabled, old.weight_technical, old.weight_communication, old.weight_culture,
      old.pass_mark, old.email_resume_reject, old.email_post_interview, old.open_mode,
      old.opens_at, old.duration_days, old.closes_at, old.credits_to_reserve
    )
  then
    raise exception 'pipeline setup is locked' using errcode = 'P0001', hint = 'pipeline_locked';
  end if;
  return new;
end;
$$;

create trigger pipelines_lock_setup
  before update on public.pipelines
  for each row execute function public.pipelines_lock_setup();

revoke all on function public.pipelines_lock_setup() from anon, authenticated, public;
