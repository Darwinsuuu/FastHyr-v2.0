# PIPE-006: Share apply link

| Field | Value |
|---|---|
| Epic | PIPE — Pipelines |
| Milestone | M2 Pipelines |
| Status | Done |
| Size | S |
| Depends on | [PIPE-001](../PIPE/PIPE-001-pipeline-model-and-state-machine.md) |
| Requirements | FR-PIPE-10 |
| Gap areas | G8 |
| Design | Frame PipelinesV2 / PipelineView (share modal) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users copy a tagged apply link for each job board with the right posting hint.

## Scope
**In:**
- Share modal component (8 sources, copied state, hints)
- `GET /pipelines/{id}/share-links`

**Out:**
- —

## Acceptance criteria
- [x] Copied URL format `…/apply/{ws}/{slug}?source={id}`
- [x] Works for scheduled pipelines too
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- PIPE-003 built the tiles: `ShareTiles` in `apps/web/components/pipelines/share-tiles.tsx` (8 sources, copied state, each board's hint) and `applyLink()` in `lib/pipelines/wizard.ts`. Wrap it in the share modal rather than building a second set.

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Auto-approved per the owner's standing rule; written before coding.)_

**API**
- `GET /v1/pipelines/{id}/share-links` (`VIEW_PIPELINES`, department scope through `PipelineRepository.detail()`, else 404): `{workspace_slug, pipeline_slug, links: [{source, url}]}`, one per source in tile order, `url = {SITE_URL}/apply/{workspace_slug}/{pipeline_slug}?source={id}`. Built by `services/pipelines.share_links()`.
- Only pipelines with a public apply page have links: drafts and cancelled pipelines (the apply page's `HIDDEN_STATUSES`) are `409 no_apply_link`. Scheduled, live, paused, out of credits and closed all return links (a closed link still shows the "closed" page).
- Schemas `ShareSource` (the 8 sources; `SourceTag` minus `direct`), `ShareLink`, `ShareLinks`. Regenerate the API client.

**Web**
- `ShareTiles` takes the links (`Record<ShareSource, string>`) instead of building them, so the modal uses the API's links and the wizard's done state passes `applyLinks()` (new, in `lib/pipelines/wizard.ts`, from `applyLink()`).
- `ShareDialog` (`components/pipelines/share-dialog.tsx`): kit `Dialog` size lg with the frame's eyebrow "Share apply link", title "Where will you post {title}?" and the body line; reads `GET …/share-links` (TanStack Query); skeleton tiles while loading, an error line with Try again. Kit `Dialog` gets an optional `eyebrow`.
- `usePipelineActions()` gains `share(summary, returnFocusTo)` and renders the dialog in `dialogs`; the list's row menu and the details header's "More actions" open it for Copy apply link, and the details header's Share apply link button is enabled (hidden for drafts/cancelled, which have no link). `copyLink` leaves `PENDING_ACTIONS` (only `topUp` stays, for BILL-006).
- Mobile first: the dialog is the kit's full-screen sheet below `md` with the 2-column tile grid, 4 columns from `sm`.

**Tests**
- API: link format and order, scheduled pipeline works, draft and cancelled 409, other workspace and out-of-department 404 (tenancy).
- Web unit: `applyLinks()`, `PENDING_ACTIONS` no longer has `copyLink`.
- e2e: publish a pipeline, open Copy apply link from the row menu, click LinkedIn, the clipboard holds `…/apply/{ws}/{slug}?source=linkedin`.

## Log
- 2026-10-27: branch `feature/pipe-006-share-apply-link`. Plan auto-approved (owner's standing rule).
- Built as planned. `ShareTiles` now leaves room under the second row on `sm`+ so a "copied" bubble never covers the hint line (it did in the wizard too). The modal uses the kit `Dialog` (sans 22 px title) rather than the frame's 28 px serif heading, like every other app dialog; the kit gained `eyebrow` for the frame's "Share apply link" label.
- Hand-tested on the seed at 360, 768, 1024 and 1440 px, light and dark: list row menu (Staff Platform Engineer, out of credits) and details header (UX Researcher, scheduled) both copy `http://fasthyr.localhost:3000/apply/acme-talent/{slug}?source={id}`; Escape returns focus to the button that opened it.
- PR #60.
