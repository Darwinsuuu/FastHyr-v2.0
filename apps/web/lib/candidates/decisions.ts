// Advance and reject (ASMT-007, ADR-017, SCREEN_SPECS.md A-02, frame PipelineView's reject
// dialog): the drafts, what the API refuses, and what to say when it does. Pure functions so the
// rules are easy to test.

import { ApiError } from "@/lib/api/client";
import { t } from "@/lib/i18n";

/** The API's limits (`app/schemas/decisions.py`). */
export const REASON_MAX = 500;
export const NOTE_MAX = 1000;

export type Decision = "advance" | "reject";

export interface DecisionDraft {
  /** The reject reason or the advance note. */
  text: string;
  /** Email the candidate (ticked by default). */
  email: boolean;
}

export const EMPTY_DRAFT: DecisionDraft = { text: "", email: true };

/** A reason is required to reject; the advance note is optional. */
export function decisionError(decision: Decision, draft: DecisionDraft): string | null {
  if (decision === "reject" && !draft.text.trim()) {
    return t("candidates.decisions.reject.reasonRequired");
  }
  return null;
}

export function advanceBody(draft: DecisionDraft): { note: string | null; send_email: boolean } {
  return { note: draft.text.trim() || null, send_email: draft.email };
}

export function rejectBody(draft: DecisionDraft): { reason: string; send_email: boolean } {
  return { reason: draft.text.trim(), send_email: draft.email };
}

/** Why the API said no, in words for the dialog. */
export function decisionFailure(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) return t("candidates.decisions.errors.notFound");
    if (error.code === "flags_to_review") return t("candidates.decisions.errors.flags");
    if (error.code === "decision_not_allowed") return t("candidates.decisions.errors.stage");
  }
  return t("candidates.decisions.errors.failed");
}
