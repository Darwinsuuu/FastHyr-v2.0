# WS-001: Company profile

| Field | Value |
|---|---|
| Epic | WS — Workspace admin |
| Milestone | M1 Access |
| Status | In review |
| Size | M |
| Depends on | [DASH-001](../DASH/DASH-001-app-shell.md), [FND-011](../FND/FND-011-storage-service-and-pdf-handling.md) |
| Requirements | FR-WS-01 |
| Gap areas | G5 |
| Design | Frame CompanyProfile |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Admins set the employer brand shown on apply pages, interviews and emails.

## Scope
**In:**
- Form + validation
- Logo/banner upload via signed URL with type/size/dimension checks; SVG sanitise/rasterise
- Branding proxy route for emails
- `GET/PUT /workspace/company-profile`

**Out:**
- —

## Acceptance criteria
- [x] Saved profile appears on apply page and email layout (email layout here; the apply page is APPLY-001, which reads this profile)
- [x] About limited to 600 chars with counter
- [x] Admin only
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

Plan auto-approved (the owner's standing rule: no plan approvals).

**API**
- `app/services/company_profile.py`, router `app/api/routers/company_profile.py`, schemas `app/schemas/company_profile.py`; all routes `require(MANAGE_WORKSPACE)` (Admin only, SECURITY.md §2).
- `GET /v1/workspace/company-profile`: every field plus `logo_url` / `banner_url` (signed, 15 min) and `updated_at`.
- `PUT /v1/workspace/company-profile`: the whole form. Company name 1–120 chars (required); website and careers page as `http(s)` URLs (a bare `acme.com` gets `https://`); industry and company size from fixed keys; HQ country as an ISO 3166 alpha-2 code; time zone checked with `zoneinfo` and copied to `workspaces.timezone` (DATABASE.md); about ≤ 600 chars. `logo_upload_id` / `banner_upload_id` attach a new image, `remove_logo` / `remove_banner` drop one. One audit row (`company_profile.updated`, changed field names only).
- `POST /v1/workspace/company-profile/branding-upload {kind}`: a signed upload URL to a temp path (`services/files.create_upload`).
- Image checks (`services/images.py`, Pillow): type from the bytes, not the browser; ≤ 2 MB; logo PNG, square, ≥ 256 px; banner PNG or JPEG; both ≤ 4096 px a side (decompression-bomb guard). Every image is decoded and re-encoded, which drops metadata (EXIF/GPS) and anything hidden after the image data; logos larger than 1024 px are scaled to 1024, banners wider than 1200 px to 1200. Stored at `branding/{workspace_id}/logo.png` and `banner.{png,jpg}` (STORAGE.md). Errors: `image_invalid`, `image_too_large`, `logo_not_square`, `logo_too_small`, `image_too_big`.
- SVG logos: rasterised to a 512 px PNG **in the browser** before upload, so the server never parses SVG (STORAGE.md allows "sanitised or rasterised"; emails can't show SVG anyway).
- `GET /v1/public/branding/{workspace_id}/{logo|banner}`: no sign-in, streams the image from Storage with a year-long cache; URLs carry `?v=<updated_at>` so a new upload gets a new URL. New setting `API_URL` (the API's public URL) builds these links.
- `branding()` returns company name + proxy URLs for emails; the email layout shows the banner, else the logo, else the name (frame copy: "No banner? Emails will show your logo instead."). The dev test email uses the saved branding so it can be checked by hand. APPLY-001 reads the candidate-safe fields for the apply page.

**Web**
- `/settings/company` (frame CompanyProfile), `<RequireAccess action="manage_workspace">`: Brand, Company details, For candidates sections; heading column beside fields from `lg`, stacked below. Logo and banner pickers with preview and Remove; website with an `https://` prefix; selects for industry, size, country (all ISO regions, names from `Intl.DisplayNames`) and time zone (all IANA zones with their UTC offset); About with a live `n / 600` counter. Save is enabled when something changed; Cancel resets the form. Form logic in `lib/company-profile`.

**Seed**: Acme Talent's profile uses the new keys and gets a company size and careers page (no images; they live in Storage).

**Tests**: image checks (unit), GET/PUT/upload/proxy round trip against local Supabase, Admin-only and tenancy (another workspace's Admin can't read it), email layout fallback, web form helpers.

## Log
_(Branch name, decisions, deviations, PR links, review files.)_

- 2026-10-02: branch `feature/next-after-wizard-ps1pxe`. Picked as the next task because it is the last open dependency of APPLY-001 (public apply page).
- Decisions: SVG logos are rasterised to a 512 px PNG in the browser (STORAGE.md allows "sanitised or rasterised"; email clients can't show SVG, and the server never parses SVG). Industry and company size are stored as keys (`technology`, `51-200`), country as ISO alpha-2 (`PH`). The banner has no minimum size ("1200 × 400 recommended" in the frame is advice). "Save and continue" in the frame became "Save changes" with Cancel resetting the form, since Getting started (DASH-002) isn't built. New `API_URL` setting for email image links; `tzdata` and `pillow` added to the API.
- Hand-tested as Admin (dana@acme-talent.test) at 360, 768, 1024 and 1440 px, light and dark: non-square logo refused in the browser, bad website blocked, SVG logo + JPEG banner saved and reloaded; Recruiter gets the no-access state; the dev test email shows the banner from the public branding route.
