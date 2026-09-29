-- WS-002 Departments: pipelines are filed under a department, or under "No department" (null).
-- The FK has no ON DELETE action: deleting a department moves its pipelines to No department
-- in the department service, in the same transaction, before the department row goes.

alter table public.pipelines
  add column department_id uuid,
  add constraint pipelines_department_fkey foreign key (workspace_id, department_id)
    references public.departments (workspace_id, id);

create index pipelines_workspace_id_department_id_idx
  on public.pipelines (workspace_id, department_id);
