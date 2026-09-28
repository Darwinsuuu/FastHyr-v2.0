# Storage (Supabase Storage)

All buckets are **private**. The browser gets short-lived signed URLs from the API after a permission check (ADR-006). Paths never contain names or emails.

| Bucket | Path pattern | Contents | Max size | Retention |
|---|---|---|---|---|
| `resumes` | `{workspace_id}/{application_id}/resume.pdf` | Original résumé (sanitised copy) | 10 MB | With candidate data (`compliance/PRIVACY.md`) |
| `recordings` | `{workspace_id}/{interview_id}/chunks/{attempt_id}/{seq}.webm` → `{workspace_id}/{interview_id}/recording.webm` (+ `audio.m4a`, `poster.jpg`) | Interview video/audio | ~50 MB per chunk; final file up to ~500 MB | 12 months after interview (default) |
| `branding` | `{workspace_id}/logo.{png,svg}`, `{workspace_id}/banner.{png,jpg}` | Company logo and email banner | 2 MB | While workspace exists |
| `reports` | `{workspace_id}/{report_job_id}.pdf` | Generated PDFs | — | 7 days (regenerate on demand) |
| `demo` | `{demo_session_id}/resume.pdf` | Demo résumé | 10 MB | Hard-deleted ≤ 24 h |

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
