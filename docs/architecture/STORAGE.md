# Storage (Supabase Storage)

All buckets are **private**. The browser gets short-lived signed URLs from the API after a permission check (ADR-006). Paths never contain names or emails.

| Bucket | Path pattern | Contents | Max size | Retention |
|---|---|---|---|---|
| `resumes` | `{workspace_id}/{application_id}/resume.pdf` | Original résumé (sanitised copy) | 10 MB | With candidate data (`compliance/PRIVACY.md`) |
| `recordings` | `{workspace_id}/{interview_id}/chunks/{attempt_id}/{seq}.webm` → `{workspace_id}/{interview_id}/recording.webm` (+ `audio.m4a`, `poster.jpg`) | Interview video/audio | ~50 MB per chunk; final file up to ~500 MB | 12 months after interview (default) |
| `branding` | `{workspace_id}/logo.{png,svg}`, `{workspace_id}/banner.{png,jpg}` | Company logo and email banner | 2 MB | While workspace exists |
| `reports` | `{workspace_id}/{report_job_id}.pdf` | Generated PDFs | — | 7 days (regenerate on demand) |
| `demo` | `{demo_session_id}/resume.pdf` | Demo résumé | 10 MB | Hard-deleted ≤ 24 h |

Buckets, limits and allowed file types are created by the migration `supabase/migrations/20261001120000_storage_buckets.sql`. Files that wait for a check before use go to `tmp/{workspace_id}/{upload_id}` in their bucket.

## Code (FND-011)
- `app/integrations/storage.py`: `Bucket`, the path builders above, and `SupabaseStorage` (signed upload and download URLs, info, download, upload, move, delete, recursive list) over the Storage REST API with the service key. `storage_from_settings()`; the worker keeps one in `ctx["storage"]`.
- `app/services/files.py`: `create_upload(storage, bucket, workspace_id)` returns an `upload_id` and a signed URL for a fresh temp path; `promote_pdf(...)` checks, sanitises and stores the file at its final path, then deletes the upload (safe to run twice); `remove_orphans()` for the daily cron.
- `app/services/pdfs.py`: `validate_pdf()` (≤ 10 MB, `%PDF-` header, opens, not encrypted, 1–20 pages) and `sanitise_pdf()`. Error codes: `pdf_not_pdf`, `pdf_too_large`, `pdf_malformed`, `pdf_encrypted`, `pdf_too_many_pages` (422), `upload_missing` (422), `upload_expired` (410).
- Sanitising removes `/OpenAction`, `/AA`, JavaScript, embedded files, XFA, file-attachment and media annotations, and every action except internal jumps and `http`, `https` and `mailto` links (which stay so TA can open a candidate's portfolio). The output is checked again and refused if anything active remains.

**Upload URL lifetime.** Supabase signs upload URLs for a fixed 2 hours (a server setting the hosted platform doesn't expose). The 10-minute limit is enforced by the API instead: the temp path's `upload_id` is a UUID v7 that records when the URL was issued, `promote_pdf` refuses a file created more than 10 minutes later (`upload_expired`), the token can't overwrite an existing file, and the orphan cron deletes anything never used.

## Upload flows
- **Résumé:** `POST /candidate/pipelines/{id}/resume-upload` → API returns a signed upload URL (valid 10 min) for a temp path → browser uploads → `POST /candidate/applications` references it → worker validates (magic bytes `%PDF`, page count ≤ 20, no encryption), sanitises with `pikepdf` (removes JavaScript, embedded files, actions) and moves it to the final path.
- **Recording chunks:** the session start response includes a batch of signed upload URLs (e.g. 30 × 10 s chunks); the client requests more via `POST /candidate/interviews/{token}/chunk-urls`. Each chunk is registered with `POST …/chunks` (seq, bytes). Configure the Storage per-file limit above the chunk size and the project-wide limit above the final file size.
- **Branding:** Admin uploads via signed URL; API validates type/dimensions; SVGs are sanitised (no scripts) or rasterised to PNG for email use.

## Download flows
- Signed download URLs expire in **≤ 15 minutes** and set `Content-Disposition: attachment` for résumés and reports.
- Recording playback uses a signed URL (15 min) refreshed by the player when it expires; HTTP range requests allow seeking.
- Branding images used in emails are served through an API proxy route with long cache (`/public/branding/{workspace_id}/logo`) so email clients don't hit expiring URLs.

## Deletion
Storage objects are deleted by the same service call that deletes the DB rows (retention job or candidate deletion). A daily reconciliation job removes orphans older than 24 h (e.g. abandoned temp uploads).
