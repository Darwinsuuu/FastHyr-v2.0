// Pipeline details (PIPE-007, FR-PIPE-11, frame PipelineView): the header and the Dashboard tab,
// from GET /v1/pipelines/{id} and GET /v1/pipelines/{id}/dashboard (DASH-003). Pure functions so
// the wording and the chart shapes are easy to test.

import type { components } from "@fasthyr/api-client";

import { formatNumber } from "@/lib/format";
import { t } from "@/lib/i18n";
import { SHARE_SOURCES, type ShareSource } from "@/lib/pipelines/wizard";

export type PipelineDetail = components["schemas"]["PipelineDetail"];
export type PipelineDashboard = components["schemas"]["PipelineDashboard"];

export const DETAIL_TABS = ["dashboard", "candidates", "ava", "setup"] as const;
export type DetailTab = (typeof DETAIL_TABS)[number];

/** The `?tab=` value, or the Dashboard when it's missing or unknown. */
export function parseTab(value: string | null | undefined): DetailTab {
  return DETAIL_TABS.find((tab) => tab === value) ?? "dashboard";
}

/** `/pipelines/{id}`, with `?tab=` unless it's the Dashboard. */
export function tabHref(pipelineId: string, tab: DetailTab): string {
  const base = `/pipelines/${encodeURIComponent(pipelineId)}`;
  return tab === "dashboard" ? base : `${base}?tab=${tab}`;
}

// Built from en-US parts in day-month order: en-GB writes September as "Sept".
function dateParts(value: Date, timeZone: string, weekday: boolean) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    weekday: weekday ? "short" : undefined,
    day: "numeric",
    month: "short",
    year: "numeric",
  }).formatToParts(value);
  return (type: string) => parts.find((p) => p.type === type)?.value ?? "";
}

/** "21 Jul 2026" in the workspace's time zone. */
export function longDate(value: Date, timeZone: string): string {
  const part = dateParts(value, timeZone, false);
  return `${part("day")} ${part("month")} ${part("year")}`;
}

/** "Fri, 26 Feb 2027" in the workspace's time zone. */
export function weekdayDate(value: Date, timeZone: string): string {
  const part = dateParts(value, timeZone, true);
  return `${part("weekday")}, ${part("day")} ${part("month")} ${part("year")}`;
}

/** "29 Sep" for a local calendar day from the API ("2026-09-29"). */
export function dayLabel(day: string): string {
  const part = dateParts(new Date(`${day}T00:00:00Z`), "UTC", false);
  return `${part("day")} ${part("month")}`;
}

/** The header's date: when it opened, or when it will. Nothing for a draft. */
export function openedLabel(pipeline: PipelineDetail, timeZone: string): string | null {
  if (!pipeline.opens_at || pipeline.status === "draft") return null;
  const date = longDate(new Date(pipeline.opens_at), timeZone);
  return pipeline.status === "scheduled"
    ? t("pipelines.detail.opens", { date })
    : t("pipelines.detail.opened", { date });
}

/** "1.6 days", "less than a day", or null with no assessments yet. */
export function medianDays(days: number | null | undefined): string | null {
  if (days === null || days === undefined) return null;
  if (days < 0.1) return t("pipelines.detail.underADay");
  return formatNumber(Math.round(days * 10) / 10);
}

/** Share of `whole`, rounded, as "41%"; empty when there's nothing to compare with. */
export function percentOf(part: number, whole: number): string {
  return whole > 0 ? `${Math.round((part / whole) * 100)}%` : "";
}

export interface FunnelRow {
  label: string;
  value: number;
  /** Share of the step before ("" for the first). */
  rate: string;
  fill: string;
}

/** "Where candidates are": the Candidates tab's stages, each a share of the step before. */
export function funnelRows(funnel: PipelineDashboard["funnel"]): FunnelRow[] {
  const steps: [string, number, string][] = [
    [t("pipelines.detail.funnel.applied"), funnel.applied, "bg-evergreen"],
    [t("pipelines.detail.funnel.invited"), funnel.invited, "bg-chart-2"],
    [t("pipelines.detail.funnel.interviewed"), funnel.interviewed, "bg-chart-3"],
    [t("pipelines.detail.funnel.ready"), funnel.ready_for_review + funnel.flagged, "bg-persimmon"],
  ];
  return steps.map(([label, value, fill], index) => ({
    label,
    value,
    rate: index === 0 ? "" : percentOf(value, steps[index - 1]?.[1] ?? 0),
    fill,
  }));
}

export interface ScoreBin {
  /** "40s", "90+" or "0–9". */
  label: string;
  count: number;
  /** At or above the pass mark's band. */
  passing: boolean;
}

export interface ScoreHistogram {
  bins: ScoreBin[];
  /** Index of the bin the pass-mark line sits before. */
  passIndex: number;
}

/**
 * Interview scores in tens, trimmed of the empty low bands so the chart starts at the lowest
 * score (or the pass mark's band, whichever is lower). Bands from the pass mark's up read as
 * passing; a pass mark of 75 draws its line before the 70s.
 */
export function scoreHistogram(
  scores: PipelineDashboard["scores"],
  passMark: number,
): ScoreHistogram {
  const passStart = Math.min(90, Math.floor(passMark / 10) * 10);
  const sorted = [...scores].sort((a, b) => a.start - b.start);
  const lowest = sorted.find((bin) => bin.count > 0)?.start ?? passStart;
  const from = Math.min(lowest, passStart);
  const bins = sorted
    .filter((bin) => bin.start >= from)
    .map((bin) => ({
      label: bin.start === 90 ? "90+" : bin.start === 0 ? "0–9" : `${bin.start}s`,
      count: bin.count,
      passing: bin.start >= passStart,
    }));
  return {
    bins,
    passIndex: Math.max(
      0,
      bins.findIndex((bin) => bin.passing),
    ),
  };
}

/** "LinkedIn", "Careers page", "Direct link" for the source tag on the apply link. */
export function sourceLabel(source: string): string {
  if ((SHARE_SOURCES as readonly string[]).includes(source)) {
    return t(`pipelines.share.sources.${source as ShareSource}.label`);
  }
  if (source === "direct") return t("pipelines.detail.sources.direct");
  return source;
}

export const DROP_REASONS = ["link_expired", "left_unfinished", "technical_issue"] as const;
export type DropReason = (typeof DROP_REASONS)[number];

export interface DropRow {
  reason: DropReason;
  label: string;
  description: string;
  count: number;
}

/** "Didn't finish the interview": each reason with what it means for this pipeline. */
export function dropRows(
  dropoffs: PipelineDashboard["dropoffs"],
  linkExpiryDays: number,
): DropRow[] {
  return DROP_REASONS.map((reason) => ({
    reason,
    label: t(`pipelines.detail.drops.${reason}.label`),
    description: t(`pipelines.detail.drops.${reason}.description`, { days: linkExpiryDays }),
    count: dropoffs[reason],
  }));
}

/** Everyone who didn't finish, whatever the reason. */
export function dropTotal(dropoffs: PipelineDashboard["dropoffs"]): number {
  return DROP_REASONS.reduce((sum, reason) => sum + dropoffs[reason], 0);
}
