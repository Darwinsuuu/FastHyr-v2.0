// The Pipelines page's "How candidates are moving" (frame PipelinesV2), from
// GET /v1/analytics/pipelines-flow (DASH-003). Pure functions so the wording is easy to test.

import type { components } from "@fasthyr/api-client";

import type { FlowStage } from "@/components/charts/flow-band";
import { formatNumber } from "@/lib/format";
import { plural, t } from "@/lib/i18n";

export type FlowSummary = components["schemas"]["FlowSummary"];
export type FlowRange = FlowSummary["period"]["range"];

const percent = (part: number, whole: number) =>
  whole > 0 ? `${Math.round((part / whole) * 100)}%` : undefined;

/** "+18%", "−9%" or "0%" against the period before; nothing when nobody applied then. */
export function changeNote(change: number | null): string | undefined {
  if (change === null) return undefined;
  if (change > 0) return `+${formatNumber(change)}%`;
  if (change < 0) return `−${formatNumber(Math.abs(change))}%`;
  return "0%";
}

/** The four stages, each with its share of the step before and what sits beside it. */
export function flowStages(flow: FlowSummary): FlowStage[] {
  const details = (parts: (string | false)[]) => parts.filter(Boolean).join(" · ") || undefined;
  return [
    {
      label: t("pipelines.list.flowApplied"),
      value: flow.applied,
      note: changeNote(flow.applied_change_pct),
      detail: details([
        flow.applied_change_pct !== null &&
          t(flow.period.range === "week" ? "pipelines.list.flowVsWeek" : "pipelines.list.flowVs30"),
        flow.processing > 0 && plural("pipelines.list.flowProcessing", flow.processing),
      ]),
    },
    {
      label: t("pipelines.list.flowInvited"),
      value: flow.invited,
      note: percent(flow.invited, flow.applied),
      detail: details([
        flow.not_a_match > 0 && plural("pipelines.list.flowNotMatch", flow.not_a_match),
      ]),
    },
    {
      label: t("pipelines.list.flowInterviewed"),
      value: flow.interviewed,
      note: percent(flow.interviewed, flow.invited),
      detail: details([
        flow.in_progress > 0 && plural("pipelines.list.flowInProgress", flow.in_progress),
        flow.not_started > 0 && plural("pipelines.list.flowNotStarted", flow.not_started),
      ]),
    },
    {
      label: t("pipelines.list.flowReady"),
      value: flow.ready_for_review,
      attention: true,
      detail: details([
        flow.flagged > 0 && plural("pipelines.list.flowFlagged", flow.flagged),
        flow.did_not_pass > 0 && plural("pipelines.list.flowDidNotPass", flow.did_not_pass),
      ]),
    },
  ];
}

/** "14 hours" under a day, else "1.8 days"; null when nothing was assessed in the range. */
export function medianLabel(hours: number | null): string | null {
  if (hours === null) return null;
  if (hours < 24) {
    const whole = Math.max(1, Math.round(hours));
    return plural("pipelines.list.hours", whole, { count: formatNumber(whole) });
  }
  const days = Math.round((hours / 24) * 10) / 10;
  return plural("pipelines.list.days", days, { count: formatNumber(days) });
}

/** Placeholder stages while the numbers load. */
export function emptyStages(): FlowStage[] {
  return (
    [
      "pipelines.list.flowApplied",
      "pipelines.list.flowInvited",
      "pipelines.list.flowInterviewed",
      "pipelines.list.flowReady",
    ] as const
  ).map((key) => ({ label: t(key), value: 0 }));
}
