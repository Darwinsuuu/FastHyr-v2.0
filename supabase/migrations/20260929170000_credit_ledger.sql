-- BILL-002 Credit ledger: credit batches, the append-only credit ledger, and the credit columns
-- of pipelines. Design: docs/architecture/BILLING.md and docs/architecture/DATABASE.md.
-- Only apps/api/app/services/credits.py changes these rows.

-- ---------------------------------------------------------------------------
-- Pipelines (the columns the ledger needs; PIPE-001 adds setup, schedule and lifecycle)
-- ---------------------------------------------------------------------------
create table public.pipelines (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  status text not null default 'draft' check (
    status in ('draft', 'scheduled', 'live', 'paused', 'paused_no_credits', 'closed', 'cancelled')
  ),
  credits_reserved integer not null default 0,
  credits_used integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint pipelines_workspace_id_id_key unique (workspace_id, id),
  constraint pipelines_credits_check check (credits_used between 0 and credits_reserved)
);

create trigger pipelines_set_updated_at
  before update on public.pipelines
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Credit batches: trial, plan and extra credits, each with its own expiry
-- ---------------------------------------------------------------------------
create table public.credit_batches (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  kind text not null check (kind in ('trial', 'plan', 'extra')),
  amount integer not null check (amount > 0),
  remaining integer not null,
  added_at timestamptz not null default now(),
  expires_at timestamptz not null,
  stripe_invoice_id text,
  note text,
  constraint credit_batches_workspace_id_id_key unique (workspace_id, id),
  constraint credit_batches_remaining_check check (remaining between 0 and amount)
);

create index credit_batches_workspace_id_expires_at_idx
  on public.credit_batches (workspace_id, expires_at) where remaining > 0;
-- One trial per workspace, ever (FR-BILL-02).
create unique index credit_batches_one_trial_idx
  on public.credit_batches (workspace_id) where kind = 'trial';

-- ---------------------------------------------------------------------------
-- Credit ledger (append-only): one row per credit change
-- ---------------------------------------------------------------------------
create table public.credit_ledger (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id),
  kind text not null check (
    kind in (
      'grant_trial', 'grant_plan', 'purchase', 'consume', 'reserve', 'release', 'top_up',
      'expire', 'adjust'
    )
  ),
  -- Balance change (signed); 0 for reserve moves.
  amount integer not null default 0,
  -- Change to the pipeline's reserve (signed).
  reserve_change integer not null default 0,
  pipeline_id uuid,
  -- APPLY-003 adds the foreign key once applications exist.
  application_id uuid,
  batch_id uuid,
  -- Workspace balance (unexpired credits) after this change.
  balance_after integer not null,
  -- No FK: the ledger must never change when a user is deleted. Null for system changes.
  actor_id uuid,
  created_at timestamptz not null default now(),
  constraint credit_ledger_pipeline_fkey foreign key (workspace_id, pipeline_id)
    references public.pipelines (workspace_id, id),
  constraint credit_ledger_batch_fkey foreign key (workspace_id, batch_id)
    references public.credit_batches (workspace_id, id)
);

create index credit_ledger_workspace_id_created_at_idx
  on public.credit_ledger (workspace_id, created_at);
create index credit_ledger_pipeline_id_idx on public.credit_ledger (pipeline_id);

create function public.reject_credit_ledger_change() returns trigger
language plpgsql
set search_path = ''
as $$
begin
  raise exception 'credit_ledger is append-only';
end;
$$;

create trigger credit_ledger_append_only
  before update or delete on public.credit_ledger
  for each row execute function public.reject_credit_ledger_change();

create trigger credit_ledger_no_truncate
  before truncate on public.credit_ledger
  for each statement execute function public.reject_credit_ledger_change();

revoke update, delete, truncate on public.credit_ledger from fasthyr_api;

-- ---------------------------------------------------------------------------
-- Backfill: workspaces created before this task (AUTH-003) recorded trial_granted_at but got
-- no credits. Give each its 20-credit trial, expiring 30 days after trial_granted_at.
-- ---------------------------------------------------------------------------
with trial as (
  insert into public.credit_batches (workspace_id, kind, amount, remaining, added_at, expires_at, note)
  select w.id, 'trial', 20, 20, w.trial_granted_at, w.trial_granted_at + interval '30 days', 'Free trial'
  from public.workspaces w
  where w.trial_granted_at is not null
    and not exists (
      select 1 from public.credit_batches b where b.workspace_id = w.id and b.kind = 'trial'
    )
  returning id, workspace_id, added_at
)
insert into public.credit_ledger (workspace_id, kind, amount, batch_id, balance_after, created_at)
select workspace_id, 'grant_trial', 20, id, 20, added_at from trial;

-- ---------------------------------------------------------------------------
-- Lockdown: RLS on with no policies; no privileges for the public keys.
-- ---------------------------------------------------------------------------
alter table public.pipelines enable row level security;
alter table public.credit_batches enable row level security;
alter table public.credit_ledger enable row level security;

revoke all on public.pipelines, public.credit_batches, public.credit_ledger from anon, authenticated;
revoke all on function public.reject_credit_ledger_change() from anon, authenticated, public;
