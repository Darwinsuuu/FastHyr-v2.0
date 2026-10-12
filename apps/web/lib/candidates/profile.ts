// The candidate profile (ASMT-004, FR-ASMT-07, frame CandidateProfile) from
// GET /v1/applications/{id}: the URL, the wording and the shapes the Overview cards draw. Pure
// functions so the rules are easy to test. TA users only: candidates never see any of this.

import type { components } from "@fasthyr/api-client";

import { plural, t } from "@/lib/i18n";
import { longDate } from "@/lib/pipelines/detail";

export type ApplicationProfile = components["schemas"]["ApplicationProfile"];
export type ProfileAssessment = components["schemas"]["ProfileAssessment"];
export type ProfileEvidence = components["schemas"]["Evidence"];
export type ProfileIntegrity = components["schemas"]["ProfileIntegrity"];
export type ProfileFlag = components["schemas"]["IntegrityFlag"];
export type RecordingUrl = components["schemas"]["RecordingUrl"];
export type Criterion = "technical" | "communication" | "culture";

export const CRITERIA: readonly Criterion[] = ["technical", "communication", "culture"];

export const PROFILE_TABS = ["overview", "resume", "interview"] as const;
export type ProfileTab = (typeof PROFILE_TABS)[number];

/** The `?tab=` value, or the Overview when it's missing or unknown. */
export function parseProfileTab(value: string | null | undefined): ProfileTab {
  return PROFILE_TABS.find((tab) => tab === value) ?? "overview";
}

/** The `?t=` value: whole seconds into the recording, or null. */
export function parseSeek(value: string | null | undefined): number | null {
  if (!value || !/^\d{1,5}$/.test(value)) return null;
  return Number(value);
}

/**
 * `/candidates/{candidateId}?application={id}`, with `&tab=` unless it's the Overview and
 * `&t=` (seconds) for a moment in the recording. IDs only: no personal data in URLs.
 */
export function profileHref(
  candidateId: string,
  applicationId: string,
  tab: ProfileTab = "overview",
  seconds?: number,
): string {
  const params = new URLSearchParams({ application: applicationId });
  if (tab !== "overview") params.set("tab", tab);
  if (tab === "interview" && seconds !== undefined) params.set("t", String(Math.floor(seconds)));
  return `/candidates/${encodeURIComponent(candidateId)}?${params.toString()}`;
}

/** "3:21" or "1:02:05" for a moment in the recording. */
export function clock(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = String(total % 60).padStart(2, "0");
  return hours > 0
    ? `${hours}:${String(minutes).padStart(2, "0")}:${seconds}`
    : `${minutes}:${seconds}`;
}

/** "1:52" for an average answer, "2.1s" for a response delay. */
export function answerLength(ms: number): string {
  return clock(ms);
}

export function delay(ms: number): string {
  return `${(Math.round(ms / 100) / 10).toFixed(1)}s`;
}

/** "1st", "2nd", "3rd", "11th", "22nd". */
export function ordinal(value: number): string {
  const tens = value % 100;
  if (tens >= 11 && tens <= 13) return `${value}th`;
  return `${value}${{ 1: "st", 2: "nd", 3: "rd" }[value % 10] ?? "th"}`;
}

/** The overall score's sentence: the fit or result, the gap to the pass mark, must-haves. */
export function scoreSentence(profile: ApplicationProfile, assessment: ProfileAssessment): string {
  const lead = assessment.fit
    ? t(`pipelines.candidates.fit.${assessment.fit}.label`)
    : t(
        assessment.passed
          ? "candidates.profile.score.passed"
          : "candidates.profile.score.notPassed",
      );
  const gap = assessment.overall_score - assessment.pass_mark;
  const parts = [
    gap >= 0
      ? plural("candidates.profile.score.above", gap)
      : plural("candidates.profile.score.below", -gap),
  ];
  const musts = profile.resume.must_haves;
  if (musts.length > 0) {
    const met = musts.filter((must) => must.met).length;
    parts.push(
      met === musts.length
        ? t("candidates.profile.score.allMustHaves", { total: musts.length })
        : t("candidates.profile.score.someMustHaves", { met, total: musts.length }),
    );
  }
  return `${lead}. ${parts.join(` ${t("candidates.profile.score.and")} `)}.`;
}

export interface DistributionBin {
  label: string;
  count: number;
  passing: boolean;
  /** This candidate's group. */
  own: boolean;
}

/** The pipeline's interview scores in groups (<50, 50s … 90+), marking this candidate's. */
export function distributionBins(
  distribution: { start: number; count: number }[],
  score: number,
  passMark: number,
): DistributionBin[] {
  const passStart = Math.min(90, Math.floor(passMark / 10) * 10);
  const sorted = [...distribution].sort((a, b) => a.start - b.start);
  return sorted.map((bin, index) => {
    const next = sorted[index + 1]?.start ?? 101;
    return {
      label: bin.start === 0 ? "<50" : bin.start === 90 ? "90+" : `${bin.start}s`,
      count: bin.count,
      passing: bin.start >= passStart,
      own: score >= bin.start && score < next,
    };
  });
}

/** "Likely" from 0.80, else "Possible" (A-04): confidence as words, never a percentage. */
export function confidenceWord(confidence: number): string {
  return t(
    confidence >= 0.8
      ? "candidates.profile.integrity.likely"
      : "candidates.profile.integrity.possible",
  );
}

export type IntegrityRowKey = "sameFace" | "inFrame" | "oneVoice" | "readAloud" | "timing";
export type IntegrityRowState = "passed" | "flagged" | "reviewed" | "notRun";

export interface IntegrityRow {
  key: IntegrityRowKey;
  state: IntegrityRowState;
  /** Why it didn't run, when it didn't. */
  reason?: string;
  flags: ProfileFlag[];
}

const ROW_FLAGS: Record<IntegrityRowKey, ProfileFlag["type"]> = {
  sameFace: "different_face",
  inFrame: "no_face",
  oneVoice: "second_voice",
  readAloud: "read_aloud",
  timing: "unusual_timing",
};

function notRunReason(key: IntegrityRowKey, checks: NonNullable<ProfileIntegrity["checks"]>) {
  const value =
    key === "sameFace" || key === "inFrame"
      ? checks.face
      : key === "oneVoice"
        ? checks.second_voice
        : key === "readAloud"
          ? checks.read_aloud
          : checks.timing;
  if (value === "ran") return null;
  if (value === "no_consent" || value === "voice_only" || value === "no_video") {
    return t(`candidates.profile.integrity.notRun.${value}`);
  }
  if (value === "too_short" || value === "failed")
    return t(`candidates.profile.integrity.notRun.${value}`);
  return t("candidates.profile.integrity.notRun.unknown");
}

/** One row per check (frame: face matched, one voice, stayed in frame, natural timing), with
 * its flags. A flag never rejects anyone: it waits for a person (ASMT-003). */
export function integrityRows(integrity: ProfileIntegrity): IntegrityRow[] {
  const checks = integrity.checks;
  return (Object.keys(ROW_FLAGS) as IntegrityRowKey[]).map((key) => {
    const flags = integrity.flags.filter((flag) => flag.type === ROW_FLAGS[key]);
    if (flags.some((flag) => flag.status === "open")) return { key, state: "flagged", flags };
    if (flags.length > 0) return { key, state: "reviewed", flags };
    const reason = checks
      ? notRunReason(key, checks)
      : t("candidates.profile.integrity.notRun.unknown");
    return reason ? { key, state: "notRun", reason, flags } : { key, state: "passed", flags };
  });
}

/** The score card's one-line integrity status. */
export function integritySummary(profile: ApplicationProfile): string {
  const integrity = profile.integrity;
  if (!integrity || integrity.status === "none") return t("candidates.profile.integrity.pending");
  if (integrity.status === "off") return t("candidates.profile.integrity.off");
  if (integrity.status === "failed") return t("candidates.profile.integrity.failed");
  if (profile.open_flags > 0)
    return plural("candidates.profile.integrity.toReview", profile.open_flags);
  if (integrity.flags.length > 0) return t("candidates.profile.integrity.reviewed");
  return t("candidates.profile.integrity.allClear");
}

/** "+27 points" between the first and the latest scored application, or null. */
export function historyChange(history: ApplicationProfile["history"]): number | null {
  const scored = history.filter((item) => item.overall_score !== null);
  if (scored.length < 2) return null;
  return (scored.at(-1)?.overall_score ?? 0) - (scored[0]?.overall_score ?? 0);
}

/** "Sep 2026" for the history list. */
export function monthYear(value: string, timeZone: string): string {
  return new Intl.DateTimeFormat("en-US", { month: "short", year: "numeric", timeZone }).format(
    new Date(value),
  );
}

/** "22 Sep, 9:15 AM" for the journey. */
export function journeyTime(value: string, timeZone: string): string {
  const date = new Date(value);
  const day = longDate(date, timeZone).split(" ").slice(0, 2).join(" ");
  const time = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
  return `${day}, ${time}`;
}

/** Whole hours from applying to the assessment, or null before one. */
export function hoursToAssessment(profile: ApplicationProfile): number | null {
  if (!profile.assessment) return null;
  const ms =
    new Date(profile.assessment.assessed_at).getTime() - new Date(profile.applied_at).getTime();
  return Math.max(0, Math.round(ms / 3_600_000));
}

/** Where the profile's actions sit for this member: Hiring managers only read (SECURITY.md §2). */
export interface ProfileActions {
  email: boolean;
  advance: boolean;
  reject: boolean;
  report: boolean;
}

// WORKFLOW.md §3: a TA can reject from these stages; advance only from Ready for review.
const REJECTABLE = ["invited", "interview_in_progress", "ready_for_review"];

export function profileActions(profile: ApplicationProfile, decide: boolean): ProfileActions {
  return {
    email: decide,
    advance: decide && profile.stage === "ready_for_review" && !profile.flagged,
    reject: decide && REJECTABLE.includes(profile.stage),
    report: profile.assessment !== null && profile.assessment !== undefined,
  };
}

/** Splits a summary into text and its [n] citations, so citations can be drawn as references. */
export function citations(text: string): ({ text: string } | { ref: number })[] {
  const parts: ({ text: string } | { ref: number })[] = [];
  let last = 0;
  for (const match of text.matchAll(/\s?\[(\d+)\]/g)) {
    if (match.index > last) parts.push({ text: text.slice(last, match.index) });
    parts.push({ ref: Number(match[1]) });
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push({ text: text.slice(last) });
  return parts;
}
