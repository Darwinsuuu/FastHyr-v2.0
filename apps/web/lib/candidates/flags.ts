// Reviewing integrity flags on the candidate profile (ASMT-003, SCREEN_SPECS.md A-04,
// FRAUD_INTEGRITY.md §3): the form's rules and wording. A review never changes the stage:
// confirming a concern doesn't reject anyone, the team still chooses Advance or Reject.

import type { components } from "@fasthyr/api-client";

import type { ProfileFlag } from "@/lib/candidates/profile";
import { clock } from "@/lib/candidates/profile";
import { t } from "@/lib/i18n";

export type FlagResolution = components["schemas"]["ResolveFlagRequest"]["status"];
export type ResolvedFlag = components["schemas"]["ResolvedFlag"];

export const RESOLUTIONS: readonly FlagResolution[] = ["no_concern", "concern_confirmed"];

/** The API's limit on a review note. */
export const NOTE_MAX = 1000;

/** Where "Review flag" in the Candidates row menu lands: the profile's integrity card. */
export const INTEGRITY_ANCHOR = "integrity";

export interface FlagReviewDraft {
  status: FlagResolution | null;
  note: string;
}

export type FlagReviewErrors = Partial<Record<"status" | "note", string>>;

/** What stops "Save review": no choice yet, a confirmed concern without a note, or a note
 * over the limit. Mirrors the API's `422`. */
export function flagReviewErrors(draft: FlagReviewDraft): FlagReviewErrors {
  const errors: FlagReviewErrors = {};
  const note = draft.note.trim();
  if (!draft.status) errors.status = t("candidates.profile.flagReview.errors.status");
  if (draft.status === "concern_confirmed" && !note)
    errors.note = t("candidates.profile.flagReview.errors.noteRequired");
  if (note.length > NOTE_MAX)
    errors.note = t("candidates.profile.flagReview.errors.noteTooLong", { max: NOTE_MAX });
  return errors;
}

/** The request body: the note trimmed, or left out when empty. */
export function flagReviewBody(draft: FlagReviewDraft & { status: FlagResolution }) {
  const note = draft.note.trim();
  return note ? { status: draft.status, note } : { status: draft.status };
}

/** The form's starting point: a reviewed flag starts from its review. */
export function draftFor(flag: ProfileFlag): FlagReviewDraft {
  return flag.status === "open"
    ? { status: null, note: "" }
    : { status: flag.status, note: flag.note ?? "" };
}

/** "Possible second voice" style label for one flag. */
export function flagLabel(flag: ProfileFlag): string {
  return t(`candidates.profile.flagReview.types.${flag.type}`);
}

/** "4:12–4:20", or one time when the flag is a moment. */
export function flagSpan(flag: ProfileFlag): string {
  const start = clock(flag.start_ms);
  const end = clock(flag.end_ms);
  return end === start ? start : `${start}–${end}`;
}
