# COMP-002: Notices and consent versioning

| Field | Value |
|---|---|
| Epic | COMP — Compliance |
| Milestone | M3 Intake |
| Status | In review |
| Size | S |
| Depends on | [FND-004](../FND/FND-004-api-skeleton-auth-request-context-permissions-erro.md) |
| Requirements | FR-COMP-01 |
| Gap areas | G2, G7 |
| Design | Frames Apply, DemoDeviceCheck + S-01 |
| Docs to read | [`compliance/PRIVACY.md §3`](../../compliance/PRIVACY.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Candidate notices and consents are versioned texts, shown consistently and stored with each record.

## Scope
**In:**
- `app/compliance/notices/` versioned texts + API to fetch current versions
- Web components rendering them
- Storage of version + timestamp on application/interview

**Out:**
- —

## Acceptance criteria
- [x] Changing a text requires a new version
- [x] Records keep the version they agreed to
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Auto-approved per the owner's standing rule: plans are written here and built without a separate approval.)_

**Texts (API).** `apps/api/app/compliance/notices/` holds one TOML file per version, `<kind>@v<N>.toml`, for three kinds: `apply` (apply form, PRIVACY.md §3), `interview` (device check, S-01 checkbox 1) and `biometric` (same-face check, S-01 checkbox 2). Each file has the checkbox `statement`, the longer `details` (the rest of PRIVACY.md §3: AI use, what is evaluated, a person decides, review / accommodation / deletion), `links` (`privacy`, `ai_in_hiring`, `terms`) and `choices` (wording that depends on the pipeline, e.g. `{interview}` for video + voice or voice only). Placeholders are `{company}` and the `choices` keys; the loader rejects any other.
- **Changing a text needs a new version:** `notices/versions.lock` records the SHA-256 of every released file. The loader refuses a file whose hash differs from its lock line ("copy it to `<kind>@v<N+1>.toml`") or a file with no lock line; `python -m app.compliance.notices lock` only adds lines for new files, never rewrites one. The current version of a kind is its highest `vN`.
- **Records keep their version:** old files stay forever and are still served by version. `services/consents.accept(kind, notice_id, now)` returns the `Consent(notice_id, at)` that APPLY-003 stores on `applications.consent_version / consent_at` and INTV-003 on `interviews`; an unknown id is `422 notice_unknown`, an older version is `409 notice_outdated` (the page shows the current text again).
- **API:** `GET /v1/public/notices` (current version of every kind), `GET /v1/public/notices/{kind}` (current), `GET /v1/public/notices/{kind}/{version}` (any released version, for showing what a record agreed to; unknown version 404, unknown kind 422). No sign-in, no workspace data.

**Web.** `lib/notices` (types, `fillNotice()` filling `{company}` and choice placeholders, link targets) and `components/consent/consent-checkbox.tsx`: the checkbox with the statement and links, "What this means" disclosure with the details, error line; `card` style for the apply form (frame Apply) and `plain` style for the device check (frame DemoDeviceCheck). The kit `Checkbox` gets an `error` prop (aria-invalid + described by). Server pages fetch with `loadNotice()`; client code with `useNotices()`. Shown at `/dev/ui` with the live texts. Mobile first, checked at 360, 768, 1024 and 1440 px.

**Docs.** API.md public routes, PRIVACY.md §3 (file layout and how to release a version), DATABASE.md (`interviews.biometric_consent_version` replaces the bool so the biometric text version is kept, as INTV-003 asks), AGENTS.md status, BOARD.md (COMP-002 In review, APPLY-002 Done, APPLY-003 Ready).

**Tests.** Unit: every released file matches the lock and parses; an edited file and an unlocked file are refused; placeholders are checked; the current version is the highest; `accept()` outdated / unknown. Route tests: the three routes, 404 for an unknown version and 422 for an unknown kind, no auth needed (public, no workspace data, so no tenancy test applies). Web: `fillNotice()`.

## Log
- 2026-10-02: branch `feature/consent-notices-a516ab`. Plan auto-approved (owner's rule). No `applications` or `interviews` table exists yet, so this task ships the texts, versioning, routes, `accept()` and the web component; APPLY-003 and INTV-003 add the columns and call `accept()`.
- Hand-tested at `/dev/ui` (Consent section, live texts from the API) at 360, 768, 1024 and 1440 px in Paper and Night: no horizontal scroll at 360, required + invalid state announced, "What this means" opens, voice-only wording swaps in. Screenshots in the project files under `screenshots/COMP-002/`.
- `interviews.biometric_consent` (bool) became `biometric_consent_version` in DATABASE.md so the biometric text version is kept too, as INTV-003 asks.
- Notice links go to the site's `/privacy`, `/ai-in-hiring` and `/terms`, which WEB-005 builds; until then they 404. The notice texts are first drafts for counsel review before launch (AI_HIRING_REGULATIONS.md).
