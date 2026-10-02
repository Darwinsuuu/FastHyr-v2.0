-- SCREEN-001 Résumé text extraction and PII redaction: the redacted résumé text every scoring
-- step reads. Design: docs/architecture/AI_PIPELINE.md §1 steps 1–2 and
-- docs/architecture/DATABASE.md (Candidates and applications). Only the redacted text is kept;
-- the original stays in the PDF. Only apps/api/app/services/screening.py writes these rows.

create table public.resume_texts (
  application_id uuid primary key,
  workspace_id uuid not null references public.workspaces (id),
  redacted_text text not null,
  -- Non-space characters extracted; below 200 the résumé is unreadable and gets no row.
  characters integer not null check (characters >= 0),
  pages integer not null check (pages > 0),
  -- Pages read as two columns.
  column_pages integer not null default 0 check (column_pages >= 0),
  -- How many details each kind of mask hid, e.g. {"name": 3, "email": 1}. Counts only.
  masked jsonb not null default '{}'::jsonb,
  -- The rules and prompt versions that produced the text, e.g. rules@v1+resume_redaction@v1.
  redaction_version text not null,
  created_at timestamptz not null default now(),
  -- Deleted with its application (candidate deletion, PRIVACY.md).
  constraint resume_texts_application_fkey foreign key (workspace_id, application_id)
    references public.applications (workspace_id, id) on delete cascade
);

-- Lockdown: RLS on with no policies; no privileges for the public keys.
alter table public.resume_texts enable row level security;
revoke all on public.resume_texts from anon, authenticated;
