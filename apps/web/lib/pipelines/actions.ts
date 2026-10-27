// Pipeline lifecycle actions (PIPE-005, FR-PIPE-07, frame PipelinesV2 modals): which actions ask
// first, the numbers their dialogs show, and what to say afterwards. Pure functions so the
// wording is easy to test; components/pipelines/pipeline-actions.tsx renders and calls them.

import { ApiError } from "@/lib/api/client";
import { formatNumber } from "@/lib/format";
import { plural, t } from "@/lib/i18n";
import { longDate } from "@/lib/pipelines/detail";
import type { Action } from "@/lib/permissions";
import {
  daysBetween,
  forRole,
  menuFor,
  type PipelineListItem,
  remaining,
  type RowAction,
  type RowMenuEntry,
} from "@/lib/pipelines/list";

export type LifecycleAction =
  "startNow" | "pause" | "resume" | "close" | "cancel" | "archive" | "duplicate";

export const LIFECYCLE_ACTIONS: LifecycleAction[] = [
  "startNow",
  "pause",
  "resume",
  "close",
  "cancel",
  "archive",
  "duplicate",
];

export const isLifecycleAction = (action: string): action is LifecycleAction =>
  (LIFECYCLE_ACTIONS as string[]).includes(action);

/** Resume and Duplicate change nothing anyone can lose, so they run without asking. Start now
 * asks too (not in the frame): it locks the setup, which can't be undone. */
export const CONFIRMED_ACTIONS: LifecycleAction[] = [
  "startNow",
  "pause",
  "close",
  "cancel",
  "archive",
];

// On the details page the page itself is the pipeline, its results and its setup.
const ON_THE_PAGE: RowAction[] = ["open", "viewResults", "viewSetup"];

/** The details header's "More actions" menu: the list's entries for the status without the ones
 * that open this page, plus Duplicate (frame PipelineView offers it for a locked setup), and no
 * Archive once archived. */
export function headerMenuFor(
  status: PipelineListItem["status"],
  archived: boolean,
  allowed: (action: Action) => boolean,
): RowMenuEntry[] {
  const entries = menuFor(status).filter(
    (entry) =>
      entry === "separator" ||
      !(ON_THE_PAGE.includes(entry) || entry === "duplicate" || (archived && entry === "archive")),
  );
  if (status !== "draft") {
    const separator = entries.indexOf("separator");
    entries.splice(separator < 0 ? entries.length : separator, 0, "duplicate");
  }
  return forRole(entries, allowed);
}

/** What the dialogs need about a pipeline: a list row, or the details page's pipeline with its
 * dashboard numbers. */
export type PipelineSummary = Pick<
  PipelineListItem,
  | "id"
  | "title"
  | "status"
  | "closed_reason"
  | "candidates"
  | "to_review"
  | "credits_used"
  | "credits_reserved"
  | "opens_at"
  | "closes_at"
  | "ended_at"
>;

export const summaryTitle = (summary: Pick<PipelineSummary, "title">) =>
  summary.title || t("pipelines.list.untitled");

export interface Fact {
  label: string;
  value: string;
}

const date = (value: string | null | undefined) => (value ? new Date(value) : null);

/** Whole days until it would have closed, never below 0; "—" without a closing date. */
export function daysLeft(summary: PipelineSummary, now: Date, timeZone: string): string {
  const closes = date(summary.closes_at);
  if (!closes) return "—";
  return formatNumber(Math.max(0, daysBetween(now, closes, timeZone)));
}

/** The grey box of numbers in the Close, Cancel and Archive dialogs. */
export function dialogFacts(
  action: LifecycleAction,
  summary: PipelineSummary,
  now: Date,
  timeZone: string,
): Fact[] {
  const k = (
    key:
      | "applied"
      | "toReview"
      | "daysLeft"
      | "wasOpening"
      | "creditsReturned"
      | "candidates"
      | "status",
  ) => t(`pipelines.actions.facts.${key}`);
  switch (action) {
    case "close":
      return [
        { label: k("applied"), value: formatNumber(summary.candidates) },
        { label: k("toReview"), value: formatNumber(summary.to_review) },
        { label: k("daysLeft"), value: daysLeft(summary, now, timeZone) },
      ];
    case "cancel": {
      const opens = date(summary.opens_at);
      return [
        { label: k("wasOpening"), value: opens ? longDate(opens, timeZone) : "—" },
        {
          label: k("creditsReturned"),
          value: formatNumber(Math.max(0, summary.credits_reserved - summary.credits_used)),
        },
      ];
    }
    case "archive":
      return [
        { label: k("candidates"), value: formatNumber(summary.candidates) },
        { label: k("status"), value: remaining(summary, now, timeZone).label },
      ];
    default:
      return [];
  }
}

/** The Pause dialog's two variable lines. */
export function pausePoints(summary: PipelineSummary, now: Date, timeZone: string) {
  return {
    countdown: t("pipelines.actions.pause.countdownBody", {
      when: remaining(summary, now, timeZone).label.toLowerCase(),
    }),
    carryOn: plural("pipelines.actions.pause.carryOnBody", summary.candidates),
  };
}

/** The Start now dialog's description: when it was going to open. */
export function startNowBody(summary: PipelineSummary, timeZone: string): string {
  const opens = date(summary.opens_at);
  return opens
    ? t("pipelines.actions.startNow.body", { date: longDate(opens, timeZone) })
    : t("pipelines.actions.startNow.bodyNoDate");
}

/** What the API answers each action with (only what the toast needs). */
export interface ActionResult {
  status: PipelineSummary["status"];
  notified?: number;
}

/** The toast after an action worked. */
export function successMessage(
  action: LifecycleAction,
  summary: PipelineSummary,
  result: ActionResult,
): string {
  const title = summaryTitle(summary);
  const outOfCredits = result.status === "paused_no_credits";
  switch (action) {
    case "startNow":
      return t(`pipelines.actions.done.${outOfCredits ? "startedNoCredits" : "started"}`, {
        title,
      });
    case "resume":
      return t(`pipelines.actions.done.${outOfCredits ? "resumedNoCredits" : "resumed"}`, {
        title,
      });
    case "close":
      return result.notified
        ? plural("pipelines.actions.done.closedNotified", result.notified, { title })
        : t("pipelines.actions.done.closed", { title });
    case "cancel":
      return plural(
        "pipelines.actions.done.cancelled",
        Math.max(0, summary.credits_reserved - summary.credits_used),
        { title },
      );
    case "pause":
      return t("pipelines.actions.done.paused", { title });
    case "archive":
      return t("pipelines.actions.done.archived", { title });
    case "duplicate":
      return t("pipelines.actions.done.duplicated", { title });
  }
}

/** Why an action didn't work, in words. A 409 means the pipeline moved on since the page
 * loaded (another member, or the schedule); the page refreshes so the menu matches again. */
export function failureMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409) return t("pipelines.actions.failed.moved");
    if (error.status === 404) return t("pipelines.actions.failed.missing");
  }
  return t("pipelines.actions.failed.other");
}
