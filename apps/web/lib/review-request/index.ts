// The human review request page (ASMT-008, SCREEN_SPECS.md S-03) at `/review-request/{token}`
// on the site host, from GET /v1/public/review-requests/{token}. No sign-in: the token in the
// rejection email is the key, and the page shows only the company and the job title.

import type { components } from "@fasthyr/api-client";

export type ReviewLink = components["schemas"]["ReviewLink"];
export type ReviewLinkState = ReviewLink["state"];

/** The API's limit for the candidate's message. */
export const MESSAGE_MAX = 1000;

/** What the card shows: the link's state, or `sent` right after this visit's request (the
 * API answers `requested` either way). */
export type ReviewCardState = ReviewLinkState | "sent";

export function cardState(link: ReviewLink, sentNow: boolean): ReviewCardState {
  return sentNow && link.state === "requested" ? "sent" : link.state;
}

/** Where the expired and unavailable states send the candidate: the careers page, else the
 * company's website. */
export function contactHref(company: ReviewLink["company"]): string | null {
  return company.careers_url || company.website || null;
}
