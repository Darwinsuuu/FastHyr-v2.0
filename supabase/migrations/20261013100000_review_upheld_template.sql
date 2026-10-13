-- ASMT-008 Human review requests: the tenth candidate email, `review_upheld`, tells the candidate
-- a person looked at the decision again and kept it (the "Request sent" page promises the outcome
-- by email). Workspaces get the default the first time their templates are read (MSG-001).

alter table public.email_templates drop constraint email_templates_key_check;
alter table public.email_templates add constraint email_templates_key_check check (
  key in (
    'interview_invitation', 'interview_reminder', 'finish_interview', 'interview_received',
    'next_stage', 'reject_resume', 'reject_interview', 'role_closed', 'review_received',
    'review_upheld'
  )
);
