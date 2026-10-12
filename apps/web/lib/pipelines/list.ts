import type { components } from "@fasthyr/api-client";

import { plural, t } from "@/lib/i18n";
import type { Action } from "@/lib/permissions";

// The Pipelines list (PIPE-004, FR-PIPE-08, frame PipelinesV2).

export type PipelineListItem = components["schemas"]["PipelineListItem"];
export type PipelineList = components["schemas"]["PipelineList"];
export type PipelineTab = "live" | "scheduled" | "closed" | "drafts" | "all";

export const PIPELINE_TABS: PipelineTab[] = ["live", "scheduled", "closed", "drafts", "all"];
export const PAGE_SIZES = [5, 10, 25] as const;
export type PageSize = (typeof PAGE_SIZES)[number];

/** Open pipelines closing within this many days are shown in amber (frame PipelinesV2). */
export const CLOSING_SOON_DAYS = 14;

type Status = PipelineListItem["status"];
const OPEN: Status[] = ["live", "paused", "paused_no_credits"];
const ENDED: Status[] = ["closed", "cancelled"];

export const isOpen = (status: Status) => OPEN.includes(status);
export const hasEnded = (status: Status) => ENDED.includes(status);

/** Year, month and day of `value` on the wall clock of `timeZone`, as a UTC midnight. */
function calendarDay(value: Date, timeZone: string): number {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(value);
  const part = (type: string) => Number(parts.find((p) => p.type === type)?.value);
  return Date.UTC(part("year"), part("month") - 1, part("day"));
}

/** Whole calendar days from `from` to `to` in the workspace's time zone (0 = same day). */
export function daysBetween(from: Date, to: Date, timeZone: string): number {
  return Math.round((calendarDay(to, timeZone) - calendarDay(from, timeZone)) / 86_400_000);
}

/** "2 Sep", with the year when it isn't this year: "18 Aug 2025". */
export function shortDate(value: Date, now: Date, timeZone: string): string {
  const parts = (date: Date) =>
    new Intl.DateTimeFormat("en-US", {
      timeZone,
      day: "numeric",
      month: "short",
      year: "numeric",
    }).formatToParts(date);
  const part = (all: Intl.DateTimeFormatPart[], type: string) =>
    all.find((p) => p.type === type)?.value ?? "";
  const these = parts(value);
  const year = part(these, "year");
  const text = `${part(these, "day")} ${part(these, "month")}`;
  return year === part(parts(now), "year") ? text : `${text} ${year}`;
}

export type Emphasis = "normal" | "soon" | "blocked" | "upcoming" | "muted";

export interface Remaining {
  label: string;
  emphasis: Emphasis;
}

/** The "Days remaining" column: days left while open, when it opens, or when it ended. */
export function remaining(item: PipelineListItem, now: Date, timeZone: string): Remaining {
  const at = (value: string | null | undefined) => (value ? new Date(value) : null);
  if (isOpen(item.status)) {
    const closes = at(item.closes_at);
    if (!closes) return { label: "—", emphasis: "normal" };
    const days = daysBetween(now, closes, timeZone);
    const label =
      days <= 0 ? t("pipelines.list.closesToday") : plural("pipelines.list.daysLeft", days);
    if (item.status === "paused_no_credits") return { label, emphasis: "blocked" };
    const soon = item.status === "live" && days <= CLOSING_SOON_DAYS;
    return { label, emphasis: soon ? "soon" : "normal" };
  }
  if (item.status === "scheduled") {
    const opens = at(item.opens_at);
    if (!opens) return { label: "—", emphasis: "upcoming" };
    const days = daysBetween(now, opens, timeZone);
    const label =
      days <= 0
        ? t("pipelines.list.opensToday")
        : days === 1
          ? t("pipelines.list.opensTomorrow")
          : t("pipelines.list.opensIn", { count: days });
    return { label, emphasis: "upcoming" };
  }
  if (item.status === "draft")
    return { label: t("pipelines.list.notPublished"), emphasis: "muted" };
  const ended = at(item.ended_at);
  const key = item.status === "cancelled" ? "cancelledOn" : "closedOn";
  return {
    label: ended ? t(`pipelines.list.${key}`, { date: shortDate(ended, now, timeZone) }) : "—",
    emphasis: "muted",
  };
}

export type CreditTone = "normal" | "low" | "out" | "muted";

/** Credit bar colour: amber from 80% of the reserve, red when it's used up, grey once ended. */
export function creditTone(
  item: Pick<PipelineListItem, "status" | "credits_used" | "credits_reserved">,
): CreditTone {
  if (hasEnded(item.status) || item.status === "draft") return "muted";
  if (item.credits_reserved <= 0) return "normal";
  const ratio = item.credits_used / item.credits_reserved;
  return ratio >= 1 ? "out" : ratio >= 0.8 ? "low" : "normal";
}

/** Share of the reserve used, 0–100, for the bar. */
export function creditPercent(
  item: Pick<PipelineListItem, "credits_used" | "credits_reserved">,
): number {
  if (item.credits_reserved <= 0) return 0;
  return Math.min(100, Math.round((item.credits_used / item.credits_reserved) * 100));
}

/** Row menu entries per status (frame PipelinesV2). `wired` entries work now; the lifecycle
 * actions arrive with PIPE-005, Copy apply link with PIPE-006 and Top up with BILL-006. */
export type RowAction =
  | "open"
  | "copyLink"
  | "viewSetup"
  | "editSetup"
  | "continueSetup"
  | "startNow"
  | "pause"
  | "resume"
  | "close"
  | "cancel"
  | "topUp"
  | "viewResults"
  | "archive";

export type RowMenuEntry = RowAction | "separator";

export function menuFor(status: Status): RowMenuEntry[] {
  switch (status) {
    case "live":
      return ["open", "copyLink", "viewSetup", "separator", "pause", "close"];
    case "paused_no_credits":
      return ["topUp", "open", "copyLink", "separator", "close"];
    case "paused":
      return ["resume", "open", "copyLink", "separator", "close"];
    case "scheduled":
      return ["editSetup", "startNow", "copyLink", "separator", "cancel"];
    case "draft":
      return ["continueSetup"];
    default:
      return ["viewResults", "separator", "archive"];
  }
}

export const DESTRUCTIVE_ACTIONS: RowAction[] = ["close", "cancel"];

/** Where a link entry goes; null for actions that aren't links. */
export function actionHref(action: RowAction, pipelineId: string): string | null {
  const id = encodeURIComponent(pipelineId);
  switch (action) {
    case "open":
    case "viewResults":
      return `/pipelines/${id}`;
    case "viewSetup":
      return `/pipelines/${id}?tab=setup`;
    case "editSetup":
    case "continueSetup":
      return `/pipelines/${id}/edit`;
    default:
      return null;
  }
}

/** Morning, afternoon or evening in the viewer's own time. */
export function greetingKey(now: Date): "morning" | "afternoon" | "evening" {
  const hour = now.getHours();
  return hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
}

/** What each row action needs (lib/permissions.ts, mirrors the API matrix). */
export const ACTION_PERMISSION: Record<RowAction, Action> = {
  open: "view_pipelines",
  copyLink: "view_pipelines",
  viewSetup: "view_pipelines",
  viewResults: "view_pipelines",
  editSetup: "edit_pipelines",
  continueSetup: "edit_pipelines",
  startNow: "change_pipeline_status",
  pause: "change_pipeline_status",
  resume: "change_pipeline_status",
  close: "change_pipeline_status",
  cancel: "change_pipeline_status",
  archive: "change_pipeline_status",
  topUp: "top_up_pipeline",
};

/** The row menu a role gets: entries it can't use are left out, and so are separators that
 * would end up first, last or doubled. */
export function menuForRole(status: Status, allowed: (action: Action) => boolean): RowMenuEntry[] {
  const entries = menuFor(status).filter(
    (entry) => entry === "separator" || allowed(ACTION_PERMISSION[entry]),
  );
  return entries.filter(
    (entry, index) =>
      entry !== "separator" ||
      (index > 0 && index < entries.length - 1 && entries[index - 1] !== "separator"),
  );
}
