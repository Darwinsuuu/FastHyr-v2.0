-- FND-013 OpenAI integration layer: one ai_calls row per model call (every try), with the
-- model, prompt version, tokens, cost and latency, so each AI step's cost and speed can be
-- tracked (AI_PIPELINE.md §7). No prompt or output text is stored here. Design: DATABASE.md.

create table public.ai_calls (
  id uuid primary key default gen_random_uuid(),
  -- Null for calls outside a workspace (the public demo).
  workspace_id uuid references public.workspaces (id),
  purpose text not null,
  -- The row the call was about (an application, interview…); no foreign key, any table.
  entity_id uuid,
  model text not null,
  prompt_version text not null,
  input_tokens integer not null default 0,
  output_tokens integer not null default 0,
  audio_seconds numeric(10, 2),
  -- Null when the model has no price configured (OPENAI_PRICES).
  cost_usd numeric(12, 6),
  latency_ms integer not null,
  status text not null check (status in ('ok', 'invalid_output', 'error')),
  created_at timestamptz not null default now()
);

create index ai_calls_workspace_id_created_at_idx on public.ai_calls (workspace_id, created_at);
create index ai_calls_purpose_created_at_idx on public.ai_calls (purpose, created_at);

-- Lockdown: RLS on with no policies; no privileges for the public keys.
alter table public.ai_calls enable row level security;
revoke all on public.ai_calls from anon, authenticated;
