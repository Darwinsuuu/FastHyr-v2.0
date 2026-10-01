# FND-011: Storage service and PDF handling

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | In review |
| Size | M |
| Depends on | [FND-004](../FND/FND-004-api-skeleton-auth-request-context-permissions-erro.md) |
| Requirements | NFR-02 |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/STORAGE.md`](../../architecture/STORAGE.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Files move between browser and Supabase Storage only through permission-checked signed URLs, and uploaded PDFs are validated and sanitised.

## Scope
**In:**
- Buckets (resumes, recordings, branding, reports, demo) created by migration/config
- `integrations/storage.py`: signed upload/download URLs, move, delete
- PDF validation (magic bytes, size, pages, encryption) and pikepdf sanitising
- Orphan reconciliation cron

**Out:**
- —

## Acceptance criteria
- [x] Signed URLs expire ≤ 15 min
- [x] Malformed/encrypted PDFs rejected with clear error codes
- [x] Sanitised PDF has no JS/embedded files (test fixture)
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Unit tests with PDF fixtures

## Implementation plan
**Buckets**: a migration inserts the five private buckets into `storage.buckets` with their size limits and allowed types (resumes and demo 10 MB PDF, recordings 500 MB webm/m4a/jpeg, branding 2 MB png/svg/jpeg, reports 50 MB PDF), so local and hosted projects match. `supabase/config.toml` raises the project-wide limit to 500 MiB for final recordings.

**Integration** (`app/integrations/storage.py`): `Bucket` enum, path builders (STORAGE.md patterns, IDs only, plus `tmp/{workspace_id}/{upload_id}` for uploads waiting to be checked) and `SupabaseStorage`, which calls the Storage REST API with the service key: signed upload URL, signed download URL (≤ 15 min, capped in code; `download=` sets `Content-Disposition: attachment`), info, download, upload, move, delete and a recursive list. Outages raise `StorageUnavailableError`.

**Upload expiry**: Supabase fixes signed upload URLs at 2 hours (a server setting the hosted platform doesn't expose). So upload URLs always point at a fresh temp path whose ID is a UUID v7 (it carries the time it was issued), uploads can't overwrite, and `claim_upload()` refuses a file that arrived more than 10 minutes after the URL was issued (`upload_expired`). A late upload is never used and the orphan cron deletes it.

**PDF handling** (`app/services/pdfs.py`): `validate_pdf()` checks magic bytes, size (≤ 10 MB), that pikepdf can open it, encryption and page count (≤ 20), raising `AppError`s with stable codes: `pdf_not_pdf`, `pdf_too_large`, `pdf_malformed`, `pdf_encrypted`, `pdf_too_many_pages`. `sanitise_pdf()` removes document and page actions (`/OpenAction`, `/AA`), the `/JavaScript` and `/EmbeddedFiles` name trees, XFA, action and file-attachment/rich-media annotations and outline actions, then rewrites the file so the dropped objects are gone.

**Service** (`app/services/files.py`): `promote_pdf()` downloads a temp upload, validates, sanitises, uploads the clean copy to the final path and deletes the temp file. APPLY-003 and SCREEN-001 call it from their jobs.

**Orphan cron**: `reconcile_storage_orphans` (daily) deletes `tmp/` uploads and demo files older than 24 hours. Later tasks add checks for final paths whose rows are gone.

**Tests**: unit tests with generated PDF fixtures (valid, not a PDF, truncated, encrypted, too many pages, with JavaScript, embedded file and launch actions → sanitised output has none); integration tests against local Storage (signed URL expiry ≤ 15 min, upload → promote → download, late upload refused, orphan cleanup). CI stops skipping `storage-api` so these run there.

## Log
- 2026-10-01: branch `feature/storage-pdf-e38yhp`. Plan auto-approved (Darwin's standing rule: no plan approvals).
- Deviation: Supabase signs upload URLs for a fixed 2 hours (`UPLOAD_SIGNED_URL_EXPIRATION_TIME` is a server setting, not a per-call option, and hosted projects don't expose it). Download URLs are 15 minutes (capped in code). For uploads the 10-minute limit is enforced by the API: the temp path's UUID v7 records when the URL was issued, `promote_pdf` refuses a file created more than 10 minutes later (`upload_expired`), the token can't overwrite, and the orphan cron deletes leftovers.
- Decision: sanitising keeps `http`, `https` and `mailto` links and internal jumps (résumés link to portfolios and LinkedIn); every other action goes, including `javascript:` URIs and actions chained with `/Next`.
- Decision: no new endpoints. The résumé upload endpoints come with APPLY-002/003, which call `create_upload` and `promote_pdf`.
- Hand test (local Supabase Storage): an upload URL from `create_upload` accepted a browser `PUT` once and refused a second (409); `promote_pdf` stored a sanitised copy (no active content) and deleted the temp file, and a rerun returned the same bytes; the signed download URL's token lasted 900 s and the response had `Content-Disposition: attachment; filename=resume.pdf`; a 16-minute URL was refused; an encrypted PDF was refused with `pdf_encrypted` and deleted, then `upload_missing`; the orphan cleanup deleted a temp upload only once it was over 24 h old; the publishable key could not read (404) or write (403) the resumes bucket.
- Tests: `tests/unit/test_pdfs.py`, `tests/unit/test_files.py`, `tests/integration/test_storage.py`. CI no longer skips `storage-api`, so the integration tests run there.
