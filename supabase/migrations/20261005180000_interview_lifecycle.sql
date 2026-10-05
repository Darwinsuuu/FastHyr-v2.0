-- INTV-007 Interview lifecycle: held "Finish your interview" emails, re-invites that supersede
-- the old link in one transaction, and the drop-off view the dashboards read. Design:
-- docs/architecture/DATABASE.md, docs/architecture/NOTIFICATIONS.md §1 and
-- docs/product/WORKFLOW.md §3-4.

-- A held email is written but waits for an event to schedule it: the "Finish your interview"
-- email is written when an attempt starts (the only time the link token is at hand) and is
-- scheduled 1 hour after the interview is left unfinished. The dispatcher never sends one.
alter table public.email_messages drop constraint email_messages_status_check;
alter table public.email_messages add constraint email_messages_status_check check (
  status in (
    'held', 'scheduled', 'cancelled', 'sending', 'sent', 'delivered', 'bounced', 'complained',
    'failed'
  )
);

-- A re-invite points the old interview at the new one before the new one is inserted (only one
-- live interview per application), so the reference is checked at commit.
alter table public.interviews drop constraint interviews_superseded_by_fkey;
alter table public.interviews add constraint interviews_superseded_by_fkey
  foreign key (superseded_by) references public.interviews (id) deferrable initially deferred;

-- One row per live interview that isn't finished and has a drop-off reason (FR-INTV-08):
-- link_expired, left_unfinished or technical_issue. dropped_at is when the link expired, or when
-- the last attempt ended. Overview and the pipeline dashboard count these (DASH-003, PIPE-007).
create view public.v_dropoff_reasons with (security_invoker = true) as
select
  i.workspace_id,
  a.pipeline_id,
  p.department_id,
  i.application_id,
  i.id as interview_id,
  i.drop_reason,
  i.status,
  case
    when i.drop_reason = 'link_expired' then i.expires_at
    else coalesce(
      (select max(t.ended_at) from public.interview_attempts t where t.interview_id = i.id),
      i.expires_at
    )
  end as dropped_at
from public.interviews i
join public.applications a
  on a.workspace_id = i.workspace_id and a.id = i.application_id
join public.pipelines p
  on p.workspace_id = a.workspace_id and p.id = a.pipeline_id
where i.superseded_by is null
  and i.status <> 'completed'
  and i.drop_reason is not null;

revoke all on public.v_dropoff_reasons from anon, authenticated;
