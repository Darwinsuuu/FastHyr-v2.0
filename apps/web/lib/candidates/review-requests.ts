// Human review requests on the candidate profile (ASMT-008, ADR-015, SCREEN_SPECS.md A-03):
// which resolutions a request offers, what the API refuses, and what to say when it does. Pure
// functions so the rules are easy to test.

import type { components } from "@fasthyr/api-client";

import { ApiError } from "@/lib/api/client";
import { t } from "@/lib/i18n";

export type ProfileReviewRequest = components["schemas"]["ProfileReviewRequest"];
export type ReviewOutcome = "uphold" | "override";

/** The API's limit (`app/schemas/review_requests.py`). */
export const RESOLUTION_NOTE_MAX = 1000;

/** The buttons the banner shows: Uphold always; override while the decision still stands
 * (automated or a person's own rejection). */
export function reviewOutcomes(request: ProfileReviewRequest): ReviewOutcome[] {
  return request.can_override ? ["uphold", "override"] : ["uphold"];
}

/** The i18n key for an outcome's button and dialog: overriding a résumé decision invites the
 * candidate to interview, overriding an interview decision moves them to Ready for review. */
export function outcomeKey(
  request: ProfileReviewRequest,
  outcome: ReviewOutcome,
): "uphold" | "invite" | "ready" {
  if (outcome === "uphold") return "uphold";
  return request.decision_type === "resume" ? "invite" : "ready";
}

/** A note is required either way ("Only your team sees this"). */
export function resolutionError(note: string): string | null {
  return note.trim() ? null : t("candidates.reviewRequest.noteRequired");
}

export function resolutionBody(
  outcome: ReviewOutcome,
  note: string,
): { outcome: ReviewOutcome; note: string } {
  return { outcome, note: note.trim() };
}

/** Why the API said no, in words for the dialog. */
export function resolutionFailure(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) return t("candidates.reviewRequest.errors.notFound");
    if (error.code === "review_request_resolved") {
      return t("candidates.reviewRequest.errors.resolved");
    }
    if (error.code === "override_not_allowed") return t("candidates.reviewRequest.errors.stage");
  }
  return t("candidates.reviewRequest.errors.failed");
}
