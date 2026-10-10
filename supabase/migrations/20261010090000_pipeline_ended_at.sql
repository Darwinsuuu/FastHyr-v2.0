-- PIPE-004 Pipelines list: when a pipeline closed or was cancelled, for "Closed 2 Sep" and
-- "Cancelled 18 Aug" and for sorting the Closed tab. `closes_at` is only the planned date, and a
-- pipeline closed by hand or cancelled ended earlier. Set by apps/api/app/services/pipelines.py.
-- Expand-only.

alter table public.pipelines
  add column ended_at timestamptz,
  add constraint pipelines_ended_check check (
    ended_at is null or status in ('closed', 'cancelled')
  );

-- Pipelines that ended before this column: on their planned date when closed on schedule, else
-- the last time the row changed (the close or cancel itself, for seed and test data).
update public.pipelines
set ended_at = case when closed_reason = 'schedule' then closes_at else updated_at end
where status in ('closed', 'cancelled');
