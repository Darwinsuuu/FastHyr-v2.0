-- FND-011 Storage: the five private buckets (STORAGE.md), created here so local and hosted
-- projects match. Nothing is public: the browser only gets short-lived signed URLs from the API
-- (ADR-006), and no storage.objects policies exist for anon or authenticated, so the public keys
-- can't read or write files. Size limits and types are a first gate; the API checks contents.
-- Expand-only: re-running it updates the limits.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('resumes', 'resumes', false, 10485760, array['application/pdf']),
  (
    'recordings',
    'recordings',
    false,
    524288000,
    array['video/webm', 'audio/webm', 'audio/mp4', 'image/jpeg']
  ),
  ('branding', 'branding', false, 2097152, array['image/png', 'image/jpeg', 'image/svg+xml']),
  ('reports', 'reports', false, 52428800, array['application/pdf']),
  ('demo', 'demo', false, 10485760, array['application/pdf'])
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;
