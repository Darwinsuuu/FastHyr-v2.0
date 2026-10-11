"use client";

import { ArrowCounterClockwiseIcon } from "@phosphor-icons/react";
import { type UseQueryResult, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { type ReactNode, useState } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { BarChart } from "@/components/charts/bar-chart";
import { ChartFrame } from "@/components/charts/chart-frame";
import { HorizontalBars } from "@/components/charts/horizontal-bars";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError, api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";
import { plural, t } from "@/lib/i18n";
import { can } from "@/lib/permissions";
import {
  dayLabel,
  dropRows,
  dropTotal,
  funnelRows,
  longDate,
  medianDays,
  percentOf,
  type PipelineDashboard,
  type PipelineDetail,
  scoreHistogram,
  sourceLabel,
  tabHref,
  weekdayDate,
} from "@/lib/pipelines/detail";
import { creditPercent, creditTone, hasEnded } from "@/lib/pipelines/list";

const CREDIT_BAR = {
  normal: "bg-evergreen",
  low: "bg-signal-watch",
  out: "bg-signal-gap",
  muted: "bg-chart-muted",
};

/** The Dashboard tab (frame PipelineView, FR-PIPE-11): how this one pipeline is doing, all from
 * GET /v1/pipelines/{id}/dashboard (DASH-003). */
export function PipelineDashboardTab({
  pipeline,
  query,
}: {
  pipeline: PipelineDetail;
  query: UseQueryResult<PipelineDashboard>;
}) {
  if (query.isError) {
    return (
      <p className="rounded-lg border border-line bg-surface-raised p-6 text-[15px] text-ink-muted">
        {t("pipelines.detail.dashboardLoadFailed")}
      </p>
    );
  }
  const data = query.data;
  if (!data) return <DashboardSkeleton />;
  return (
    <div className="flex flex-col gap-4 md:gap-5">
      <Kpis pipeline={pipeline} data={data} />
      {/* Side by side only from xl: beside the sidebar at lg the bars get too short. */}
      <div className="grid gap-4 md:gap-5 xl:grid-cols-2">
        <Card
          titleId="pipeline-funnel"
          title={t("pipelines.detail.funnelTitle")}
          hint={t("pipelines.detail.funnelHint")}
        >
          <HorizontalBars
            title={t("pipelines.detail.funnelTitle")}
            size={10}
            wideLabels
            rows={funnelRows(data.funnel).map((row) => ({
              label: row.label,
              value: row.value,
              note: row.rate || undefined,
              fill: row.fill,
            }))}
          />
        </Card>
        <DailyCard data={data} />
      </div>
      <div className="grid gap-4 md:gap-5 lg:grid-cols-2 xl:grid-cols-3">
        <ScoresCard data={data} />
        <SourcesCard data={data} />
        <DropsCard pipeline={pipeline} data={data} />
      </div>
    </div>
  );
}

function Card({
  titleId,
  title,
  hint,
  aside,
  children,
  className,
}: {
  titleId: string;
  title: string;
  hint?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      aria-labelledby={titleId}
      className={cn(
        "flex min-w-0 flex-col gap-4 rounded-lg border border-line bg-surface-raised p-4 md:p-5",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-0.5">
          <h2 id={titleId} className="type-title">
            {title}
          </h2>
          {hint && <p className="text-[13px] leading-[18px] text-ink-muted">{hint}</p>}
        </div>
        {aside}
      </div>
      {children}
    </section>
  );
}

// -- KPIs -------------------------------------------------------------------------------------

function Kpi({
  label,
  children,
  className,
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "-mt-px -ml-px flex min-w-0 flex-col gap-1.5 border-t border-l border-line p-4 md:px-[22px] md:py-5",
        className,
      )}
    >
      <span className="type-label text-ink-muted uppercase">{label}</span>
      {children}
    </div>
  );
}

const BIG =
  "text-[26px] leading-8 font-[650] tracking-[-0.01em] text-ink tabular-nums md:text-[30px] md:leading-9";
const SMALL = "text-[13px] leading-[18px] text-ink-muted";

function Kpis({ pipeline, data }: { pipeline: PipelineDetail; data: PipelineDashboard }) {
  const { kpis, timezone } = data;
  const median = medianDays(kpis.median_days_to_assessment);
  const tone = creditTone({
    status: pipeline.status,
    credits_used: kpis.credits_used,
    credits_reserved: kpis.credits_reserved,
  });
  const used = formatNumber(kpis.credits_used);
  const total = formatNumber(kpis.credits_reserved);
  return (
    <section
      aria-label={t("pipelines.detail.kpisLabel")}
      // One card split by hairlines; each cell draws its top and left line over the card's edge.
      className="grid grid-cols-2 overflow-hidden rounded-lg border border-line bg-surface-raised md:grid-cols-3 xl:grid-cols-5"
    >
      <Kpi label={t("pipelines.detail.kpis.candidates")}>
        <span className={BIG}>{formatNumber(kpis.candidates)}</span>
        <span className={SMALL}>
          <strong className="font-[650] text-signal-strong">
            +{formatNumber(kpis.new_this_week)}
          </strong>{" "}
          {t("pipelines.detail.kpis.newThisWeek")}
        </span>
      </Kpi>
      <Kpi label={t("pipelines.detail.kpis.ready")}>
        <span className={cn(BIG, kpis.ready_for_review > 0 && "text-persimmon-ink")}>
          {formatNumber(kpis.ready_for_review)}
        </span>
        {kpis.ready_for_review > 0 && (
          <Link
            href={tabHref(pipeline.id, "candidates")}
            className="self-start text-[13px] leading-[18px] font-semibold text-persimmon-ink hover:underline"
          >
            {t("pipelines.detail.kpis.reviewThem")}
          </Link>
        )}
      </Kpi>
      <Kpi label={t("pipelines.detail.kpis.timeToAssessment")}>
        {median ? (
          <span className={BIG}>
            {median}{" "}
            <span className="text-[15px] font-semibold text-ink-muted">
              {t("pipelines.detail.kpis.days")}
            </span>
          </span>
        ) : (
          <span className={cn(BIG, "text-ink-muted")}>—</span>
        )}
        <span className={SMALL}>
          {median
            ? t("pipelines.detail.kpis.timeToAssessmentHint")
            : t("pipelines.detail.kpis.noAssessments")}
        </span>
      </Kpi>
      <Kpi label={t("pipelines.detail.kpis.creditsUsed")}>
        <span className={BIG}>
          {used} <span className="text-[15px] font-semibold text-ink-muted">/ {total}</span>
        </span>
        <div
          role="img"
          aria-label={t("pipelines.detail.kpis.creditsLabel", { used, total })}
          className="mt-1 h-1.5 w-full overflow-hidden rounded-pill bg-surface-sunk"
        >
          <div
            className={cn("h-full rounded-pill", CREDIT_BAR[tone])}
            style={{
              width: `${creditPercent({ credits_used: kpis.credits_used, credits_reserved: kpis.credits_reserved })}%`,
            }}
          />
        </div>
      </Kpi>
      <RemainingKpi pipeline={pipeline} data={data} timeZone={timezone} />
    </section>
  );
}

function RemainingKpi({
  pipeline,
  data,
  timeZone,
}: {
  pipeline: PipelineDetail;
  data: PipelineDashboard;
  timeZone: string;
}) {
  const { kpis } = data;
  // Five cells: the last one fills the row on phones (2 columns) and tablets (3 columns).
  const span = "col-span-2 xl:col-span-1";
  if (hasEnded(pipeline.status)) {
    const ended = pipeline.ended_at ? longDate(new Date(pipeline.ended_at), timeZone) : null;
    const key = pipeline.status === "cancelled" ? "cancelledOn" : "closedOn";
    return (
      <Kpi label={t("pipelines.detail.kpis.daysRemaining")} className={span}>
        <span className={cn(BIG, "text-ink-muted")}>—</span>
        {ended && (
          <span className={SMALL}>{t(`pipelines.detail.kpis.${key}`, { date: ended })}</span>
        )}
      </Kpi>
    );
  }
  if (pipeline.status === "scheduled") {
    return (
      <Kpi label={t("pipelines.detail.kpis.daysRemaining")} className={span}>
        <span className={cn(BIG, "text-ink-muted")}>—</span>
        <span className={SMALL}>{t("pipelines.detail.kpis.notOpenYet")}</span>
      </Kpi>
    );
  }
  return (
    <Kpi label={t("pipelines.detail.kpis.daysRemaining")} className={span}>
      <span className={BIG}>
        {kpis.days_remaining === null || kpis.days_remaining === undefined
          ? "—"
          : formatNumber(kpis.days_remaining)}
      </span>
      <span className={SMALL}>
        {kpis.closes_at
          ? t("pipelines.detail.kpis.closes", {
              date: weekdayDate(new Date(kpis.closes_at), timeZone),
            })
          : t("pipelines.detail.kpis.noCloseDate")}
      </span>
    </Kpi>
  );
}

// -- Charts -----------------------------------------------------------------------------------

function DailyCard({ data }: { data: PipelineDashboard }) {
  const total = data.daily.reduce((sum, day) => sum + day.applicants, 0);
  const title = t("pipelines.detail.dailyTitle");
  return (
    <Card
      titleId="pipeline-daily"
      title={title}
      hint={t("pipelines.detail.dailyHint", { total: formatNumber(total) })}
    >
      <BarChart
        title={title}
        series={[{ name: t("pipelines.detail.dailySeries"), fill: "bg-evergreen" }]}
        data={data.daily.map((point) => ({
          label: dayLabel(point.day),
          values: [point.applicants],
        }))}
        showValues={false}
        labelEvery={2}
        phoneLabelEvery={4}
        height={140}
      />
    </Card>
  );
}

function ScoresCard({ data }: { data: PipelineDashboard }) {
  const title = t("pipelines.detail.scoresTitle");
  const histogram = scoreHistogram(data.scores, data.pass_mark);
  return (
    <Card
      titleId="pipeline-scores"
      title={title}
      hint={
        <>
          {t("pipelines.detail.scoresHint", { interviewed: formatNumber(data.interviewed) })}
          {data.interviewed > 0 && (
            <>
              {" · "}
              <strong className="font-semibold text-ink">
                {t("pipelines.detail.scoresPassed", {
                  passed: formatNumber(data.passed),
                  mark: data.pass_mark,
                })}
              </strong>
            </>
          )}
        </>
      }
    >
      {data.interviewed === 0 ? (
        <Empty>{t("pipelines.detail.scoresEmpty")}</Empty>
      ) : (
        <BarChart
          title={title}
          series={[{ name: t("pipelines.detail.scoresSeries"), fill: "bg-evergreen" }]}
          data={histogram.bins.map((bin) => ({ label: bin.label, values: [bin.count] }))}
          fillFor={(_, index) => (histogram.bins[index]?.passing ? undefined : "bg-chart-muted")}
          marker={{ beforeIndex: histogram.passIndex, label: t("pipelines.detail.passMark") }}
          height={130}
        />
      )}
    </Card>
  );
}

function SourcesCard({ data }: { data: PipelineDashboard }) {
  const title = t("pipelines.detail.sourcesTitle");
  const top = Math.max(1, ...data.sources.map((row) => row.applicants));
  const rows = data.sources.map((row) => ({
    label: sourceLabel(row.source),
    applicants: row.applicants,
    passRate: row.resume_pass_rate === null ? "—" : `${row.resume_pass_rate}%`,
  }));
  return (
    <Card titleId="pipeline-sources" title={title} hint={t("pipelines.detail.sourcesHint")}>
      {rows.length === 0 ? (
        <Empty>{t("pipelines.detail.sourcesEmpty")}</Empty>
      ) : (
        <>
          <ChartFrame
            title={title}
            columns={[
              t("pipelines.detail.sourcesApplicants"),
              t("pipelines.detail.sourcesPassRate"),
            ]}
            data={rows.map((row) => ({
              label: row.label,
              values: [formatNumber(row.applicants), row.passRate],
            }))}
          >
            <div className="grid grid-cols-[minmax(0,1fr)_minmax(48px,1.2fr)_auto_auto] items-center gap-x-3 gap-y-3 text-[14px]">
              <span className="text-[12px] font-semibold text-ink-muted">
                {t("pipelines.detail.sourcesSource")}
              </span>
              <span className="text-[12px] font-semibold text-ink-muted">
                {t("pipelines.detail.sourcesApplicants")}
              </span>
              <span />
              <span className="text-right text-[12px] font-semibold text-ink-muted">
                {t("pipelines.detail.sourcesPassRate")}
              </span>
              {rows.map((row) => (
                <SourceRow key={row.label} row={row} top={top} />
              ))}
            </div>
          </ChartFrame>
          <p className="text-[12px] leading-4 text-ink-muted">
            {t("pipelines.detail.sourcesNote")}
          </p>
        </>
      )}
    </Card>
  );
}

function SourceRow({
  row,
  top,
}: {
  row: { label: string; applicants: number; passRate: string };
  top: number;
}) {
  return (
    <>
      <span className="truncate text-ink">{row.label}</span>
      <span className="overflow-hidden rounded-pill bg-surface">
        <span
          className="block h-2 rounded-pill bg-evergreen"
          style={{ width: `${(row.applicants / top) * 100}%` }}
        />
      </span>
      <span className="text-right font-bold text-ink tabular-nums">
        {formatNumber(row.applicants)}
      </span>
      <span className="text-right text-ink-muted tabular-nums">{row.passRate}</span>
    </>
  );
}

// -- Drop-offs and Re-invite all --------------------------------------------------------------

function DropsCard({ pipeline, data }: { pipeline: PipelineDetail; data: PipelineDashboard }) {
  const { workspace } = useShell();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { dropoffs } = data;
  const total = dropTotal(dropoffs);
  const count = dropoffs.reinvitable;
  const canReinvite = can(workspace.role, "decide_candidates");
  // INTV-007 refuses cancelled and archived pipelines.
  const allowed = pipeline.status !== "cancelled" && !pipeline.archived_at;

  const reinvite = useMutation({
    mutationFn: async () =>
      unwrap(
        await api.POST("/v1/pipelines/{pipeline_id}/reinvite", {
          params: { path: { pipeline_id: pipeline.id } },
          body: { scope: "all_unfinished" },
        }),
      ),
    onSuccess: (result) => {
      toast({ title: plural("pipelines.detail.reinvited", result.reinvited), tone: "success" });
      void queryClient.invalidateQueries({
        queryKey: keys.pipelineDashboard(workspace.id, pipeline.id),
      });
    },
  });

  return (
    <Card
      titleId="pipeline-drops"
      title={t("pipelines.detail.dropsTitle")}
      hint={
        total > 0
          ? plural("pipelines.detail.dropsHint", total, {
              percent: percentOf(total, dropoffs.invited) || "0%",
            })
          : t("pipelines.detail.dropsNone")
      }
      className="lg:col-span-2 xl:col-span-1"
    >
      <ul className="flex flex-col divide-y divide-line">
        {dropRows(dropoffs, pipeline.link_expiry_days).map((row) => (
          <li
            key={row.reason}
            className="flex items-center justify-between gap-3 py-2.5 first:pt-0"
          >
            <span className="flex min-w-0 flex-col">
              <span className="text-[14px] font-semibold text-ink">{row.label}</span>
              <span className="text-[13px] leading-[18px] text-ink-muted">{row.description}</span>
            </span>
            <strong className="text-[17px] font-bold text-ink tabular-nums">
              {formatNumber(row.count)}
            </strong>
          </li>
        ))}
      </ul>
      {canReinvite && (
        <Button
          variant="secondary"
          className="mt-auto w-full"
          icon={<ArrowCounterClockwiseIcon aria-hidden="true" className="size-5" />}
          disabled={count === 0 || !allowed}
          onClick={() => {
            setError(null);
            setConfirming(true);
          }}
        >
          {count > 0
            ? plural("pipelines.detail.reinvite", count)
            : t("pipelines.detail.reinviteNone")}
        </Button>
      )}
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={t("pipelines.detail.reinviteTitle")}
        description={plural("pipelines.detail.reinviteBody", count)}
        confirmLabel={t("pipelines.detail.reinviteConfirm")}
        onConfirm={async () => {
          setError(null);
          try {
            await reinvite.mutateAsync();
          } catch (caught) {
            setError(
              caught instanceof ApiError && caught.code === "reinvite_not_allowed"
                ? t("pipelines.detail.reinviteNotAllowed")
                : t("pipelines.detail.reinviteFailed"),
            );
            throw caught;
          }
        }}
      >
        {error && (
          <p role="alert" className="text-[14px] text-signal-gap">
            {error}
          </p>
        )}
      </ConfirmDialog>
    </Card>
  );
}

function Empty({ children }: { children: ReactNode }) {
  return <p className="py-6 text-center text-[14px] text-ink-muted">{children}</p>;
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-4 md:gap-5" aria-busy="true">
      <Skeleton className="h-[220px] rounded-lg md:h-[236px] xl:h-[118px]" />
      <div className="grid gap-4 md:gap-5 lg:grid-cols-2">
        <Skeleton className="h-[260px] rounded-lg" />
        <Skeleton className="h-[260px] rounded-lg" />
      </div>
    </div>
  );
}
