"use client";

import {
  CheckCircleIcon,
  CheckIcon,
  FlagIcon,
  MinusCircleIcon,
  PlayIcon,
  QuestionIcon,
  ScalesIcon,
  SparkleIcon,
  WarningIcon,
} from "@phosphor-icons/react";
import Link from "next/link";
import type { ReactNode } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { FlagReviewList } from "@/components/candidates/flag-review";
import { BarChart } from "@/components/charts/bar-chart";
import { Legend } from "@/components/charts/chart-frame";
import { HorizontalBars } from "@/components/charts/horizontal-bars";
import { LineChart } from "@/components/charts/line-chart";
import { RadarChart } from "@/components/charts/radar-chart";
import { ScoreBar } from "@/components/ui/score-bar";
import { WeightedCalc } from "@/components/ui/weighted-calc";
import {
  type ApplicationProfile,
  answerLength,
  CRITERIA,
  citations,
  clock,
  delay,
  distributionBins,
  historyChange,
  hoursToAssessment,
  integrityRows,
  integritySummary,
  journeyTime,
  monthYear,
  ordinal,
  type ProfileAssessment,
  type ProfileEvidence,
  profileHref,
  scoreSentence,
} from "@/lib/candidates/profile";
import { INTEGRITY_ANCHOR } from "@/lib/candidates/flags";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";
import { plural, t } from "@/lib/i18n";
import { can } from "@/lib/permissions";
import { longDate, sourceLabel } from "@/lib/pipelines/detail";

const SERIES_FILL = ["bg-evergreen", "bg-chart-2", "bg-chart-3"];

interface Navigate {
  /** Opens the AI interview tab at this moment of the recording. */
  onSeek: (ms: number) => void;
  onResume: () => void;
}

/** The Overview tab (frame CandidateProfile): how the score was reached, the evidence behind it
 * and how the candidate compares. Before an assessment exists it says where they are. */
export function ProfileOverview({
  profile,
  onSeek,
  onResume,
}: { profile: ApplicationProfile } & Navigate) {
  const assessment = profile.assessment;
  // With flags the integrity card is the review panel (A-04): full width, near the top.
  const reviewing = hasFlags(profile);
  if (!assessment) {
    return (
      <div className="flex flex-col gap-4 md:gap-5">
        <NotAssessed profile={profile} />
        {reviewing && <IntegrityCard profile={profile} onSeek={onSeek} />}
        <div className="grid gap-4 md:grid-cols-2 md:gap-5 xl:grid-cols-3">
          <ResumeMatchCard profile={profile} onResume={onResume} />
          {profile.integrity && !reviewing && <IntegrityCard profile={profile} onSeek={onSeek} />}
          <JourneyCard profile={profile} />
        </div>
        {profile.history.length > 1 && <HistoryCard profile={profile} />}
      </div>
    );
  }
  const name = firstName(profile.candidate.name);
  return (
    <div className="flex flex-col gap-4 md:gap-5">
      <div className="grid gap-4 md:gap-5 xl:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <ScoreCard profile={profile} assessment={assessment} />
        <CalcCard profile={profile} assessment={assessment} />
      </div>
      {reviewing && <IntegrityCard profile={profile} onSeek={onSeek} />}
      <WhyCard assessment={assessment} onSeek={onSeek} onResume={onResume} />
      {profile.comparison && (
        <div className="grid gap-4 md:gap-5 lg:grid-cols-2">
          <DistributionCard profile={profile} assessment={assessment} name={name} />
          <CompareCard profile={profile} assessment={assessment} name={name} />
        </div>
      )}
      {profile.history.length > 1 ? (
        <div className="grid gap-4 md:gap-5 lg:grid-cols-2">
          <TopicsCard assessment={assessment} name={name} onSeek={onSeek} />
          <HistoryCard profile={profile} />
        </div>
      ) : (
        <TopicsCard assessment={assessment} name={name} onSeek={onSeek} wide />
      )}
      <div className="grid gap-4 md:gap-5 lg:grid-cols-2">
        <SummaryCard assessment={assessment} onSeek={onSeek} onResume={onResume} />
        <PointsCard assessment={assessment} />
      </div>
      <div
        className={cn(
          "grid gap-4 md:grid-cols-2 md:gap-5",
          reviewing ? "xl:grid-cols-3" : "xl:grid-cols-4",
        )}
      >
        <ResumeMatchCard profile={profile} onResume={onResume} />
        <AnswersCard profile={profile} assessment={assessment} />
        {!reviewing && <IntegrityCard profile={profile} onSeek={onSeek} />}
        <JourneyCard profile={profile} />
      </div>
      <p className="flex gap-3 rounded-lg border border-line bg-surface p-4 text-[14px] leading-[21px] text-ink md:p-5">
        <ScalesIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-evergreen" />
        <span>
          <strong className="font-[650]">{t("candidates.profile.fairness")}</strong>{" "}
          {t("candidates.profile.fairnessBody")}
        </span>
      </p>
    </div>
  );
}

function hasFlags(profile: ApplicationProfile): boolean {
  return profile.integrity?.status === "ready" && profile.integrity.flags.length > 0;
}

function firstName(name: string): string {
  return name.trim().split(/\s+/)[0] || name;
}

function Card({
  titleId,
  title,
  hint,
  aside,
  children,
  className,
  id,
}: {
  titleId: string;
  title: ReactNode;
  hint?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <section
      id={id}
      aria-labelledby={titleId}
      className={cn(
        "flex min-w-0 scroll-mt-24 flex-col gap-4 rounded-lg border border-line bg-surface-raised p-4 md:p-5",
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

function NotAssessed({ profile }: { profile: ApplicationProfile }) {
  const stage = profile.stage;
  const known = [
    "processing_resume",
    "resume_not_match",
    "invited",
    "interview_in_progress",
    "scoring",
  ] as const;
  const key = known.find((value) => value === stage) ?? "other";
  return (
    <section className="flex flex-col gap-1.5 rounded-lg border border-line bg-surface-raised p-4 md:p-5">
      <h2 className="type-title">{t("candidates.profile.notAssessed.title")}</h2>
      <p className="text-[15px] leading-6 text-ink-muted">
        {t(`candidates.profile.notAssessed.${key}`)}
      </p>
    </section>
  );
}

// -- Score and calculation -------------------------------------------------------------------

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-t border-line py-2.5 text-[14px] first:border-t-0">
      <span className="text-ink-muted">{label}</span>
      <strong className="text-right font-[650] text-ink tabular-nums">{children}</strong>
    </div>
  );
}

function ScoreCard({
  profile,
  assessment,
}: {
  profile: ApplicationProfile;
  assessment: ProfileAssessment;
}) {
  const comparison = profile.comparison;
  return (
    <Card titleId="profile-score" title={t("candidates.profile.score.title")}>
      <div className="flex items-baseline gap-2">
        <span className="font-display text-[56px] leading-[56px] font-[560] text-ink tabular-nums">
          {assessment.overall_score}
        </span>
        <span className="text-[18px] text-ink-muted">{t("candidates.profile.score.outOf")}</span>
      </div>
      <p className="text-[15px] leading-[22px] text-ink">{scoreSentence(profile, assessment)}</p>
      <div className="flex flex-col">
        <Fact label={t("candidates.profile.score.passMark")}>{assessment.pass_mark}</Fact>
        {comparison && (
          <>
            <Fact label={t("candidates.profile.score.rank")}>
              {t("candidates.profile.score.rankValue", {
                rank: ordinal(comparison.rank),
                total: formatNumber(comparison.interviewed),
              })}
            </Fact>
            <Fact label={t("candidates.profile.score.average")}>{comparison.average}</Fact>
          </>
        )}
        <Fact label={t("candidates.profile.score.evidence")}>
          {plural("candidates.profile.score.moments", assessment.evidence_count)}
        </Fact>
        <Fact label={t("candidates.profile.score.integrity")}>{integritySummary(profile)}</Fact>
      </div>
    </Card>
  );
}

function CalcCard({
  profile,
  assessment,
}: {
  profile: ApplicationProfile;
  assessment: ProfileAssessment;
}) {
  const locked = profile.pipeline.rubric_locked_at;
  return (
    <Card
      titleId="profile-calc"
      title={t("score.howWeGot", { total: assessment.overall_score })}
      hint={t("candidates.profile.calc.hint")}
    >
      <WeightedCalc
        items={CRITERIA.map((name) => ({
          label: t(`candidates.profile.criteria.${name}`),
          score: assessment.criteria[name].score,
          weight: assessment.criteria[name].weight,
        }))}
        passMark={assessment.pass_mark}
        note={
          locked
            ? t("candidates.profile.calc.locked", {
                date: longDate(new Date(locked), profile.timezone),
              })
            : t("candidates.profile.calc.lockedNoDate")
        }
      />
    </Card>
  );
}

// -- Why each score --------------------------------------------------------------------------

function EvidenceSource({
  evidence,
  onSeek,
  onResume,
}: {
  evidence: ProfileEvidence;
} & Navigate) {
  if (
    evidence.source === "interview" &&
    evidence.start_ms !== null &&
    evidence.start_ms !== undefined
  ) {
    const time = clock(evidence.start_ms);
    const start = evidence.start_ms;
    return (
      <button
        type="button"
        onClick={() => onSeek(start)}
        aria-label={t("candidates.profile.why.watch", { time })}
        className="inline-flex min-h-8 items-center gap-1 rounded-pill bg-evergreen-soft px-2.5 text-[13px] font-[650] text-evergreen tabular-nums hover:bg-evergreen hover:text-on-evergreen"
      >
        <PlayIcon aria-hidden="true" weight="fill" className="size-3" />
        {time}
      </button>
    );
  }
  return (
    <button
      type="button"
      onClick={onResume}
      className="inline-flex min-h-8 items-center rounded-pill bg-surface-sunk px-2.5 text-[13px] font-[650] text-ink hover:bg-line"
    >
      {t("candidates.profile.why.resume")}
    </button>
  );
}

function WhyCard({ assessment, onSeek, onResume }: { assessment: ProfileAssessment } & Navigate) {
  return (
    <Card
      titleId="profile-why"
      title={t("candidates.profile.why.title")}
      hint={t("candidates.profile.why.hint")}
    >
      <div className="grid gap-5 xl:grid-cols-3 xl:gap-0">
        {CRITERIA.map((name, index) => {
          const criterion = assessment.criteria[name];
          const label = t(`candidates.profile.criteria.${name}`);
          return (
            <div
              key={name}
              className={cn(
                "flex min-w-0 flex-col gap-4",
                index > 0 && "border-t border-line pt-5 xl:border-t-0 xl:border-l xl:pt-0",
                "xl:px-5 xl:first:pl-0 xl:last:pr-0",
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="inline-flex items-center gap-2 text-[15px] font-[650] text-ink">
                  <span
                    aria-hidden="true"
                    className={cn("size-2.5 rounded-pill", SERIES_FILL[index])}
                  />
                  {label}
                </span>
                <strong className="text-[22px] font-[650] text-ink tabular-nums">
                  {criterion.score}
                </strong>
              </div>
              <ul
                aria-label={t("candidates.profile.why.signals", { criterion: label })}
                className="flex flex-col gap-2.5"
              >
                {criterion.signals.map((signal) => (
                  <li
                    key={signal.name}
                    className="grid grid-cols-[minmax(0,1fr)_72px_28px] items-center gap-2.5 text-[13px]"
                  >
                    <span className="truncate text-ink">{signal.name}</span>
                    <ScoreBar value={signal.score} label={signal.name} size={6} />
                    <strong className="text-right font-[650] text-ink tabular-nums">
                      {signal.score}
                    </strong>
                  </li>
                ))}
              </ul>
              <div className="flex flex-col gap-2.5">
                <span className="type-label text-ink-muted uppercase">
                  {t("candidates.profile.why.evidence")}
                </span>
                {criterion.evidence.map((evidence) => (
                  <figure
                    key={`${evidence.source}-${evidence.start_ms}-${evidence.quote}`}
                    className="flex flex-col gap-2 rounded-md bg-surface p-3"
                  >
                    <blockquote className="text-[14px] leading-[21px] text-ink">
                      “{evidence.quote}”
                    </blockquote>
                    <figcaption className="flex flex-wrap items-center gap-2 text-[12px] text-ink-muted">
                      <EvidenceSource evidence={evidence} onSeek={onSeek} onResume={onResume} />
                      <span>{evidence.label}</span>
                    </figcaption>
                  </figure>
                ))}
              </div>
              {criterion.held_back && (
                <p className="flex gap-2 rounded-md border border-line p-3 text-[13px] leading-[19px] text-ink">
                  <WarningIcon
                    aria-hidden="true"
                    className="mt-0.5 size-4 shrink-0 text-signal-watch"
                  />
                  <span>
                    <strong className="font-[650]">{t("candidates.profile.why.heldBack")}</strong>{" "}
                    {criterion.held_back}
                  </span>
                </p>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}

// -- Comparisons -----------------------------------------------------------------------------

function DistributionCard({
  profile,
  assessment,
  name,
}: {
  profile: ApplicationProfile;
  assessment: ProfileAssessment;
  name: string;
}) {
  const comparison = profile.comparison;
  if (!comparison) return null;
  const title = t("candidates.profile.distribution.title", { name });
  const bins = distributionBins(
    comparison.distribution,
    assessment.overall_score,
    assessment.pass_mark,
  );
  const passIndex = Math.max(
    0,
    bins.findIndex((bin) => bin.passing),
  );
  return (
    <Card
      titleId="profile-distribution"
      title={title}
      hint={plural("candidates.profile.distribution.hint", comparison.interviewed)}
    >
      <BarChart
        title={title}
        series={[{ name: t("candidates.profile.distribution.series"), fill: "bg-chart-3" }]}
        data={bins.map((bin) => ({ label: bin.label, values: [bin.count] }))}
        fillFor={(_, index) => {
          const bin = bins[index];
          if (bin?.own) return "bg-persimmon";
          return bin?.passing ? undefined : "bg-chart-muted";
        }}
        marker={{
          beforeIndex: passIndex,
          label: t("candidates.profile.distribution.passMark", { mark: assessment.pass_mark }),
        }}
        height={140}
        legend={false}
      />
      <Legend
        items={[
          {
            label: t("candidates.profile.distribution.own", {
              name,
              score: assessment.overall_score,
            }),
            swatch: "bg-persimmon",
          },
          { label: t("candidates.profile.distribution.passed"), swatch: "bg-chart-3" },
          { label: t("candidates.profile.distribution.notPassed"), swatch: "bg-chart-muted" },
        ]}
      />
    </Card>
  );
}

function CompareCard({
  profile,
  assessment,
  name,
}: {
  profile: ApplicationProfile;
  assessment: ProfileAssessment;
  name: string;
}) {
  const comparison = profile.comparison;
  if (!comparison) return null;
  return (
    <Card
      titleId="profile-compare"
      title={t("candidates.profile.compare.title")}
      hint={t("candidates.profile.compare.hint")}
    >
      <div className="flex flex-col gap-5">
        {CRITERIA.map((criterion) => {
          const label = t(`candidates.profile.criteria.${criterion}`);
          const own = assessment.criteria[criterion].score;
          const { average, passed_average: passedAverage } = comparison.criteria[criterion];
          const delta = own - average;
          return (
            <div key={criterion} className="flex flex-col gap-2.5">
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-[14px] font-[650] text-ink">{label}</span>
                <span
                  className={cn(
                    "text-[13px] font-[650] tabular-nums",
                    delta >= 0 ? "text-signal-strong" : "text-ink-muted",
                  )}
                >
                  {t("candidates.profile.compare.delta", {
                    delta: delta >= 0 ? `+${delta}` : `${delta}`,
                  })}
                </span>
              </div>
              <HorizontalBars
                title={label}
                size={8}
                max={100}
                rows={[
                  { label: name, value: own, fill: "bg-evergreen" },
                  ...(passedAverage !== null && passedAverage !== undefined
                    ? [
                        {
                          label: t("candidates.profile.compare.passedAvg"),
                          value: passedAverage,
                          fill: "bg-chart-3",
                        },
                      ]
                    : []),
                  {
                    label: t("candidates.profile.compare.pipelineAvg"),
                    value: average,
                    fill: "bg-chart-muted",
                  },
                ]}
              />
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function TopicsCard({
  assessment,
  name,
  onSeek,
  wide = false,
}: {
  assessment: ProfileAssessment;
  name: string;
  onSeek: (ms: number) => void;
  /** The whole row: the chart sits beside the list from md. */
  wide?: boolean;
}) {
  const title = t("candidates.profile.topics.title");
  const scored = assessment.topics.filter(
    (topic) => topic.score !== null && topic.score !== undefined,
  );
  return (
    <Card
      titleId="profile-topics"
      title={title}
      hint={t("candidates.profile.topics.hint", { name })}
    >
      {assessment.topics.length === 0 ? (
        <p className="text-[14px] text-ink-muted">{t("candidates.profile.topics.empty")}</p>
      ) : (
        <div className={cn("flex flex-col gap-4", wide && "md:flex-row md:items-center")}>
          {scored.length >= 3 && (
            <RadarChart
              title={title}
              className={cn(wide && "md:w-1/2")}
              axes={scored.map((topic) => topic.title)}
              series={[
                { name, values: scored.map((topic) => topic.score ?? 0), variant: "primary" },
                {
                  name: t("candidates.profile.topics.avgSeries"),
                  values: scored.map((topic) => topic.average ?? 0),
                  variant: "comparison",
                },
              ]}
            />
          )}
          <ul className="flex min-w-0 flex-1 flex-col divide-y divide-line">
            {assessment.topics.map((topic) => (
              <li key={topic.index}>
                <button
                  type="button"
                  onClick={() => onSeek(topic.start_ms)}
                  aria-label={`${topic.title}. ${t("candidates.profile.why.watch", {
                    time: clock(topic.start_ms),
                  })}`}
                  className="grid min-h-11 w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 py-2 text-left hover:bg-surface"
                >
                  <span className="flex min-w-0 flex-col">
                    <span className="truncate text-[14px] text-ink">{topic.title}</span>
                    <span className="text-[12px] text-ink-muted tabular-nums">
                      {clock(topic.start_ms)}
                    </span>
                  </span>
                  <span className="flex items-baseline gap-2 text-right">
                    <strong className="text-[15px] font-[650] text-ink tabular-nums">
                      {topic.score ?? "—"}
                    </strong>
                    <span className="w-[64px] text-[12px] text-ink-muted tabular-nums">
                      {topic.average !== null && topic.average !== undefined
                        ? t("candidates.profile.topics.average", { value: topic.average })
                        : t("candidates.profile.topics.noAverage")}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

function HistoryCard({ profile }: { profile: ApplicationProfile }) {
  const history = profile.history;
  const change = historyChange(history);
  const scored = history.filter(
    (item) => item.overall_score !== null && item.overall_score !== undefined,
  );
  const title = t("candidates.profile.history.title", { workspace: profile.workspace_name });
  return (
    <Card
      id="profile-history"
      titleId="profile-history-title"
      title={title}
      hint={plural("candidates.profile.history.hint", history.length)}
      aside={
        change !== null && (
          <strong
            className={cn(
              "text-[15px] font-[650] whitespace-nowrap tabular-nums",
              change >= 0 ? "text-signal-strong" : "text-ink-muted",
            )}
          >
            {t("candidates.profile.history.change", {
              change: change >= 0 ? `+${change}` : `${change}`,
            })}
          </strong>
        )
      }
    >
      {scored.length >= 2 && (
        <LineChart
          title={title}
          points={scored.map((item) => ({
            label: item.pipeline_title,
            value: item.overall_score ?? 0,
          }))}
        />
      )}
      <ul className="flex flex-col divide-y divide-line">
        {history.map((item) => (
          <li key={item.application_id} className="flex items-center justify-between gap-3 py-2.5">
            <div className="flex min-w-0 flex-col">
              <span className="truncate text-[14px] font-[650] text-ink">
                {item.pipeline_title}
              </span>
              <span className="text-[12px] text-ink-muted">
                {monthYear(item.applied_at, profile.timezone)} · {t(`status.stage.${item.stage}`)}
              </span>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <strong className="text-[15px] font-[650] text-ink tabular-nums">
                {item.overall_score ?? "—"}
              </strong>
              {item.current ? (
                <span className="text-[12px] text-ink-muted">
                  {t("candidates.profile.history.thisOne")}
                </span>
              ) : (
                <Link
                  href={profileHref(profile.candidate.id, item.application_id)}
                  className="inline-flex min-h-11 items-center text-[13px] font-semibold text-evergreen hover:underline md:min-h-0"
                >
                  {t("candidates.profile.history.open")}
                </Link>
              )}
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

// -- Summary, strengths and probes -----------------------------------------------------------

function SummaryCard({
  assessment,
  onSeek,
  onResume,
}: { assessment: ProfileAssessment } & Navigate) {
  const { text, refs } = assessment.summary;
  return (
    <Card
      titleId="profile-summary"
      title={
        <span className="inline-flex items-center gap-2">
          <SparkleIcon aria-hidden="true" className="size-5 text-evergreen" />
          {t("candidates.profile.summary.title")}
        </span>
      }
    >
      <p className="text-[15px] leading-6 text-ink">
        {citations(text).map((part, index) =>
          "text" in part ? (
            <span key={index}>{part.text}</span>
          ) : (
            <sup key={index} className="ml-0.5 text-[11px] font-[650] text-evergreen">
              [{part.ref}]
            </sup>
          ),
        )}
      </p>
      {refs.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="type-label text-ink-muted uppercase">
            {t("candidates.profile.summary.sources")}
          </span>
          <ol className="flex flex-col gap-1.5">
            {refs.map((ref, index) => {
              const interview =
                ref.source === "interview" && ref.start_ms !== null && ref.start_ms !== undefined;
              const start = ref.start_ms ?? 0;
              return (
                <li key={`${index}-${ref.quote}`}>
                  <button
                    type="button"
                    onClick={() => (interview ? onSeek(start) : onResume())}
                    className="grid min-h-11 w-full grid-cols-[28px_minmax(0,auto)_minmax(0,1fr)] items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px] hover:bg-surface md:min-h-0"
                  >
                    <span className="font-[650] text-evergreen">[{index + 1}]</span>
                    <span className="font-[650] whitespace-nowrap text-ink tabular-nums">
                      {interview
                        ? t("candidates.profile.summary.interviewAt", { time: clock(start) })
                        : t("candidates.profile.summary.resume")}
                    </span>
                    <span className="truncate text-ink-muted">{ref.label}</span>
                  </button>
                </li>
              );
            })}
          </ol>
        </div>
      )}
    </Card>
  );
}

function PointsCard({ assessment }: { assessment: ProfileAssessment }) {
  return (
    <section className="flex min-w-0 flex-col gap-5 rounded-lg border border-line bg-surface-raised p-4 md:p-5">
      <div className="flex flex-col gap-3">
        <h2 className="type-title">{t("candidates.profile.strengths")}</h2>
        <ul className="flex flex-col gap-2.5">
          {assessment.strengths.map((point) => (
            <li key={point.title} className="flex gap-2.5 text-[14px] leading-[21px]">
              <CheckCircleIcon
                aria-hidden="true"
                weight="fill"
                className="mt-0.5 size-5 shrink-0 text-signal-strong"
              />
              <span className="text-ink">
                {point.title} <span className="text-ink-muted">· {point.reason}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>
      <div className="flex flex-col gap-3 border-t border-line pt-5">
        <h2 className="type-title">{t("candidates.profile.probes")}</h2>
        <ul className="flex flex-col gap-2.5">
          {assessment.probes.map((point) => (
            <li key={point.title} className="flex gap-2.5 text-[14px] leading-[21px]">
              <QuestionIcon
                aria-hidden="true"
                weight="bold"
                className="mt-0.5 size-5 shrink-0 text-signal-watch"
              />
              <span className="text-ink">
                {point.title} <span className="text-ink-muted">· {point.reason}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

// -- Side cards ------------------------------------------------------------------------------

function ResumeMatchCard({
  profile,
  onResume,
}: {
  profile: ApplicationProfile;
  onResume: () => void;
}) {
  const resume = profile.resume;
  const musts = resume.must_haves;
  const met = musts.filter((must) => must.met).length;
  return (
    <Card titleId="profile-resume-match" title={t("candidates.profile.resumeMatch.title")}>
      {resume.score === null || resume.score === undefined ? (
        <p className="text-[14px] text-ink-muted">
          {t(
            resume.status === "unreadable"
              ? "candidates.profile.resumeMatch.unreadable"
              : "candidates.profile.resumeMatch.notScreened",
          )}
        </p>
      ) : (
        <>
          <p className="text-[14px] text-ink-muted">
            <strong className="text-[22px] font-[650] text-ink tabular-nums">
              {t("candidates.profile.resumeMatch.fit", { score: resume.score })}
            </strong>
            {musts.length > 0 && (
              <>
                {" · "}
                {t("candidates.profile.resumeMatch.mustHaves", { met, total: musts.length })}
              </>
            )}
          </p>
          <ul className="flex flex-col gap-2">
            {musts.map((must) => (
              <li key={must.name} className="flex gap-2 text-[14px] leading-5 text-ink">
                {must.met ? (
                  <CheckIcon
                    aria-hidden="true"
                    weight="bold"
                    className="mt-0.5 size-4 shrink-0 text-signal-strong"
                  />
                ) : (
                  <MinusCircleIcon
                    aria-hidden="true"
                    className="mt-0.5 size-4 shrink-0 text-signal-gap"
                  />
                )}
                <span>
                  {must.name}
                  <span className="sr-only">
                    {" "}
                    (
                    {t(
                      must.met
                        ? "candidates.profile.resumeMatch.met"
                        : "candidates.profile.resumeMatch.notMet",
                    )}
                    )
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
      <button
        type="button"
        onClick={onResume}
        className="mt-auto inline-flex min-h-11 items-center self-start text-[14px] font-semibold text-evergreen hover:underline md:min-h-0"
      >
        {t("candidates.profile.resumeMatch.see")}
      </button>
    </Card>
  );
}

function AnswersCard({
  profile,
  assessment,
}: {
  profile: ApplicationProfile;
  assessment: ProfileAssessment;
}) {
  const stats = assessment.answer_stats;
  if (!stats) return null;
  const avg = profile.comparison?.answer_stats;
  const rows: [string, string, string | null][] = [
    [
      t("candidates.profile.answers.length"),
      answerLength(stats.avg_answer_ms),
      avg ? answerLength(avg.avg_answer_ms) : null,
    ],
    [
      t("candidates.profile.answers.delay"),
      delay(stats.avg_response_delay_ms),
      avg ? delay(avg.avg_response_delay_ms) : null,
    ],
    [
      t("candidates.profile.answers.followUps"),
      formatNumber(stats.follow_ups),
      avg ? formatNumber(avg.follow_ups) : null,
    ],
    [
      t("candidates.profile.answers.questions"),
      formatNumber(stats.candidate_questions),
      avg ? formatNumber(avg.candidate_questions) : null,
    ],
    [
      t("candidates.profile.answers.talk"),
      `${stats.talk_time_pct}%`,
      avg ? `${avg.talk_time_pct}%` : null,
    ],
  ];
  return (
    <Card titleId="profile-answers" title={t("candidates.profile.answers.title")}>
      <dl className="flex flex-col">
        {rows.map(([label, value, average]) => (
          <div
            key={label}
            className="flex items-baseline justify-between gap-3 border-t border-line py-2.5 text-[14px] first:border-t-0"
          >
            <dt className="text-ink-muted">{label}</dt>
            <dd className="text-right whitespace-nowrap">
              <strong className="font-[650] text-ink tabular-nums">{value}</strong>
              {average && (
                <span className="ml-1.5 text-[12px] text-ink-muted tabular-nums">
                  {t("candidates.profile.answers.avg", { value: average })}
                </span>
              )}
            </dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}

const STATE_CLASSES = {
  passed: "text-signal-strong",
  flagged: "text-signal-gap",
  reviewed: "text-ink-muted",
  notRun: "text-ink-muted",
};

function IntegrityCard({
  profile,
  onSeek,
}: {
  profile: ApplicationProfile;
  onSeek: (ms: number) => void;
}) {
  const { workspace } = useShell();
  const integrity = profile.integrity;
  const title = t("candidates.profile.integrity.title");
  if (!integrity) return null;
  if (integrity.status !== "ready") {
    const key =
      integrity.status === "off"
        ? "offBody"
        : integrity.status === "failed"
          ? "failedBody"
          : "pendingBody";
    return (
      <Card id={INTEGRITY_ANCHOR} titleId="profile-integrity" title={title}>
        <p className="text-[14px] text-ink-muted">{t(`candidates.profile.integrity.${key}`)}</p>
      </Card>
    );
  }
  const rows = integrityRows(integrity);
  const checks = (
    <ul className="flex flex-col gap-3">
      {rows.map((row) => (
        <li key={row.key} className="flex flex-col gap-1.5">
          <div className="flex items-start justify-between gap-3 text-[14px]">
            <span className="text-ink">{t(`candidates.profile.integrity.rows.${row.key}`)}</span>
            <span
              className={cn(
                "inline-flex shrink-0 items-center gap-1 text-[13px] font-[650]",
                STATE_CLASSES[row.state],
              )}
            >
              {row.state === "passed" && (
                <CheckIcon aria-hidden="true" weight="bold" className="size-3.5" />
              )}
              {row.state === "flagged" && (
                <FlagIcon aria-hidden="true" weight="bold" className="size-3.5" />
              )}
              {t(`candidates.profile.integrity.states.${row.state}`)}
            </span>
          </div>
          {row.state === "notRun" && row.reason && (
            <span className="text-[12px] text-ink-muted">{row.reason}</span>
          )}
        </li>
      ))}
    </ul>
  );
  const note = (
    <p className="text-[12px] leading-[17px] text-ink-muted">
      {t("candidates.profile.integrity.note")}
    </p>
  );
  if (integrity.flags.length === 0) {
    return (
      <Card id={INTEGRITY_ANCHOR} titleId="profile-integrity" title={title}>
        {checks}
        <div className="mt-auto">{note}</div>
      </Card>
    );
  }

  const open = integrity.flags.filter((flag) => flag.status === "open");
  const reviewed = integrity.flags.filter((flag) => flag.status !== "open");
  const canResolve = can(workspace.role, "resolve_reviews");
  return (
    <Card
      id={INTEGRITY_ANCHOR}
      titleId="profile-integrity"
      title={title}
      hint={
        open.length > 0
          ? plural("candidates.profile.integrity.toReview", open.length)
          : t("candidates.profile.integrity.reviewed")
      }
    >
      <div className="grid gap-5 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-6">
        <div className="flex flex-col gap-4">
          {checks}
          {note}
        </div>
        <div className="flex flex-col gap-4">
          {open.length > 0 && (
            <>
              <p className="rounded-md bg-surface p-3 text-[13px] leading-[19px] text-ink">
                {t("candidates.profile.integrity.guidance")}
              </p>
              <FlagReviewList
                profile={profile}
                flags={open}
                canResolve={canResolve}
                onSeek={onSeek}
              />
            </>
          )}
          {reviewed.length > 0 && (
            <div className="flex flex-col gap-3">
              {open.length > 0 && (
                <h3 className="text-[13px] font-[650] text-ink-muted">
                  {t("candidates.profile.flagReview.reviewedTitle")}
                </h3>
              )}
              <FlagReviewList
                profile={profile}
                flags={reviewed}
                canResolve={canResolve}
                onSeek={onSeek}
              />
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

/** Journey steps a person took, which name who (ASMT-007, ASMT-008). */
const DECIDED_STEPS = ["advanced", "rejected", "review_upheld", "review_overridden"] as const;

function decidedStep(kind: string): kind is (typeof DECIDED_STEPS)[number] {
  return (DECIDED_STEPS as readonly string[]).includes(kind);
}

function JourneyCard({ profile }: { profile: ApplicationProfile }) {
  const hours = hoursToAssessment(profile);
  const minutes = profile.interview?.duration_seconds
    ? Math.round(profile.interview.duration_seconds / 60)
    : null;
  return (
    <Card
      titleId="profile-journey"
      title={t("candidates.profile.journey.title")}
      aside={
        hours !== null && (
          <span className="text-[12px] whitespace-nowrap text-ink-muted">
            {plural("candidates.profile.journey.hours", hours)}
          </span>
        )
      }
    >
      <ol className="flex flex-col">
        {profile.journey.map((step, index) => {
          const last = index === profile.journey.length - 1;
          const label =
            step.kind === "applied"
              ? t("candidates.profile.journey.steps.applied", {
                  source: sourceLabel(profile.source),
                })
              : step.kind === "interview_finished" && minutes !== null
                ? t("candidates.profile.journey.steps.interview_finished_minutes", { minutes })
                : decidedStep(step.kind) && step.by
                  ? t(`candidates.profile.journey.steps.${step.kind}By`, { name: step.by })
                  : t(`candidates.profile.journey.steps.${step.kind}`);
          return (
            <li key={`${step.kind}-${step.at}`} className="flex gap-3">
              <span aria-hidden="true" className="flex w-3 flex-col items-center">
                <span className="mt-1.5 size-2.5 shrink-0 rounded-pill bg-evergreen" />
                {!last && <span className="w-px flex-1 bg-evergreen-soft" />}
              </span>
              <span className={cn("flex min-w-0 flex-col", !last && "pb-3")}>
                <span className="text-[14px] text-ink">{label}</span>
                <span className="text-[12px] text-ink-muted">
                  {journeyTime(step.at, profile.timezone)}
                </span>
                {/* The advance note, reject reason or review note, for the team only. */}
                {step.note && (
                  <span className="mt-1 border-l-2 border-line pl-2.5 text-[13px] leading-[18px] break-words whitespace-pre-line text-ink-muted">
                    {step.note}
                  </span>
                )}
              </span>
            </li>
          );
        })}
      </ol>
    </Card>
  );
}
