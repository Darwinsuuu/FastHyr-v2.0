// Candidates tab of the pipeline details (PIPE-008, FR-PIPE-12/13, frame PipelineView + A-02,
// A-03) from GET /v1/pipelines/{id}/applications: stage filters, the fit explanation and the row
// menu. Pure functions so the wording and the rules are easy to test.

import type { components } from "@fasthyr/api-client";

import { profileHref } from "@/lib/candidates/profile";
import { t } from "@/lib/i18n";
import { longDate } from "@/lib/pipelines/detail";

export type PipelineCandidates = components["schemas"]["PipelineCandidates"];
export type PipelineCandidate = components["schemas"]["PipelineCandidate"];
export type CandidateFilter = keyof components["schemas"]["CandidateFilterCounts"];

/** Every stage filter, in the order the chips show. */
export const CANDIDATE_FILTERS = [
  "all",
  "processing",
  "not_a_match",
  "invited",
  "in_progress",
  "ready",
  "did_not_pass",
  "flagged",
  "review_requested",
  "advanced",
  "rejected",
] as const satisfies readonly CandidateFilter[];

/** Hiring managers see the shortlist only (SECURITY.md §2). */
export const SHORTLIST_FILTERS = ["all", "ready", "flagged", "advanced"] as const;

export const CANDIDATE_PAGE_SIZES = [10, 25, 50] as const;
export type CandidatePageSize = (typeof CANDIDATE_PAGE_SIZES)[number];

/** How often the tab re-reads while someone is being screened, interviewed or scored. */
export const POLL_MS = 15_000;

export function filtersFor(shortlist: boolean): readonly CandidateFilter[] {
  return shortlist ? SHORTLIST_FILTERS : CANDIDATE_FILTERS;
}

/** The `?stage=` value, or All when it's missing or not one the member can use. */
export function parseFilter(value: string | null | undefined, shortlist: boolean): CandidateFilter {
  return filtersFor(shortlist).find((filter) => filter === value) ?? "all";
}

/** `/pipelines/{id}?tab=candidates`, with `&stage=` unless it's All. */
export function candidatesHref(pipelineId: string, filter: CandidateFilter = "all"): string {
  const base = `/pipelines/${encodeURIComponent(pipelineId)}?tab=candidates`;
  return filter === "all" ? base : `${base}&stage=${filter}`;
}

/** Re-read while anyone's résumé is being screened or interview is running or being scored. */
export function shouldPoll(counts: PipelineCandidates["counts"] | undefined): boolean {
  return Boolean(counts && counts.processing + counts.in_progress > 0);
}

/** "21 Jul 2026" and "9:14 AM" in the workspace's time zone. */
export function appliedLabel(appliedAt: string, timeZone: string): { date: string; time: string } {
  const value = new Date(appliedAt);
  const time = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hour: "numeric",
    minute: "2-digit",
  }).format(value);
  return { date: longDate(value, timeZone), time };
}

export interface FitExplanation {
  /** "Strong fit" or "Good fit". */
  label: string;
  /** What the badge means. */
  description: string;
  /** Why this candidate has it: the résumé and interview numbers, or the flags to review. */
  why: string;
}

/**
 * ADR-011's badge with its explanation, or null before a passed interview (the cell shows "—").
 * A rejected candidate's badge is no longer shown.
 */
export function fitExplanation(
  item: PipelineCandidate,
  passMark: number | null | undefined,
): FitExplanation | null {
  if (!item.fit || item.stage === "rejected") return null;
  const label = t(`pipelines.candidates.fit.${item.fit}.label`);
  const description = t(`pipelines.candidates.fit.${item.fit}.description`, {
    mark: passMark ?? "—",
  });
  const score = item.overall_score ?? "—";
  if (item.flagged && item.flag_types.length > 0) {
    const flags = item.flag_types.map((type) => t(`pipelines.candidates.flagPhrases.${type}`));
    return {
      label,
      description,
      why: t("pipelines.candidates.fit.whyFlagged", { score, flags: flags.join("; ") }),
    };
  }
  const parts: string[] = [];
  if (item.must_haves && item.must_haves.total > 0) {
    parts.push(
      t("pipelines.candidates.fit.mustHaves", {
        met: item.must_haves.met,
        total: item.must_haves.total,
      }),
    );
  }
  parts.push(t("pipelines.candidates.fit.interview", { score }));
  let why = `${parts.join(" · ")}.`;
  if (item.strongest) {
    why += ` ${t("pipelines.candidates.fit.strongest", {
      area: t(`pipelines.candidates.criteria.${item.strongest}`),
    })}`;
  }
  return { label, description, why };
}

export type CandidateAction =
  "profile" | "resume" | "report" | "reviewFlag" | "email" | "advance" | "reject";

export type CandidateMenuEntry = CandidateAction | "separator";

export interface CandidateMenuAccess {
  /** Reject, advance and email (decide_candidates). */
  decide: boolean;
  /** Resolve integrity flags (resolve_reviews). */
  resolve: boolean;
}

// WORKFLOW.md §3: a TA can reject from these stages; advance only from Ready for review.
const REJECTABLE: readonly PipelineCandidate["stage"][] = [
  "invited",
  "interview_in_progress",
  "ready_for_review",
];

/** The row menu (FR-PIPE-13). Hiring managers get the profile and downloads only. */
export function candidateMenu(
  item: PipelineCandidate,
  access: CandidateMenuAccess,
): CandidateMenuEntry[] {
  const entries: CandidateMenuEntry[] = ["profile", "resume"];
  if (item.overall_score !== null && item.overall_score !== undefined) entries.push("report");
  if (item.flagged && access.resolve) entries.push("reviewFlag");
  if (!access.decide) return entries;
  entries.push("email");
  // Advance: Ready for review, or Flagged once every flag is resolved (A-02).
  const advance = item.stage === "ready_for_review" && !item.flagged;
  const reject = REJECTABLE.includes(item.stage);
  if (advance || reject) entries.push("separator");
  if (advance) entries.push("advance");
  if (reject) entries.push("reject");
  return entries;
}

/** The candidate's profile for this application (ASMT-004). */
export function candidateProfileHref(item: PipelineCandidate): string {
  return profileHref(item.candidate.id, item.id);
}

/**
 * Where a menu action goes, or null while its task isn't built: flag review (ASMT-003), the
 * downloads (ASMT-009) and the advance and reject dialogs (ASMT-007). View profile opens the
 * profile (ASMT-004); Email candidate opens the member's mail app.
 */
export function candidateActionHref(
  action: CandidateAction,
  item: PipelineCandidate,
): string | null {
  if (action === "email") return `mailto:${item.candidate.email}`;
  if (action === "profile") return candidateProfileHref(item);
  return null;
}
