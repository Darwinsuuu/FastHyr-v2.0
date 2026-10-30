// The share modal (PIPE-006, FR-PIPE-10) from GET /v1/pipelines/{id}/share-links.

import type { components } from "@fasthyr/api-client";

import type { ShareSource } from "@/lib/pipelines/wizard";

export type ShareLink = components["schemas"]["ShareLink"];
type PipelineStatus = components["schemas"]["Pipeline"]["status"];

/** Drafts and cancelled pipelines have no apply page, so nothing to share (the API answers
 * `409 no_apply_link`); every other status does, scheduled ones included (PIPE-006). */
export function hasApplyLink(status: PipelineStatus): boolean {
  return status !== "draft" && status !== "cancelled";
}

/** The API's share links keyed by source, as `ShareTiles` takes them. */
export function shareLinksBySource(links: ShareLink[]): Record<ShareSource, string> {
  return Object.fromEntries(links.map((link) => [link.source, link.url])) as Record<
    ShareSource,
    string
  >;
}
