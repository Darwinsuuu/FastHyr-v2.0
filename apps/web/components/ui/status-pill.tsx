import { t } from "@/lib/i18n";
import { cn } from "@/lib/cn";

// Values from docs/product/WORKFLOW.md §2 and §3. Labels live in messages/en.json.
export type PipelineStatus =
  "draft" | "scheduled" | "live" | "paused" | "paused_no_credits" | "closed" | "cancelled";

export type ApplicationStage =
  | "processing_resume"
  | "resume_not_match"
  | "invited"
  | "interview_in_progress"
  | "scoring"
  | "ready_for_review"
  | "did_not_pass"
  | "advanced"
  | "rejected";

type Tone = "live" | "active" | "attention" | "done" | "quiet";

// Never red: signal-gap is evidence, not a verdict (DESIGN_SYSTEM.md §3), so no stage reads as "failed".
const TONES: Record<Tone, { pill: string; dot: string }> = {
  live: { pill: "bg-evergreen-soft text-evergreen", dot: "bg-evergreen" },
  active: { pill: "bg-surface-sunk text-ink", dot: "bg-signal-strong" },
  attention: { pill: "bg-surface-sunk text-ink", dot: "bg-signal-watch" },
  done: { pill: "bg-evergreen text-on-evergreen", dot: "bg-on-evergreen" },
  quiet: { pill: "border border-line-strong text-ink-muted", dot: "bg-line-strong" },
};

const PIPELINE_TONE: Record<PipelineStatus, Tone> = {
  draft: "quiet",
  scheduled: "active",
  live: "live",
  paused: "attention",
  paused_no_credits: "attention",
  closed: "quiet",
  cancelled: "quiet",
};

const STAGE_TONE: Record<ApplicationStage, Tone> = {
  processing_resume: "active",
  resume_not_match: "quiet",
  invited: "live",
  interview_in_progress: "live",
  scoring: "active",
  ready_for_review: "attention",
  did_not_pass: "quiet",
  advanced: "done",
  rejected: "quiet",
};

function Pill({ tone, label, className }: { tone: Tone; label: string; className?: string }) {
  const { pill, dot } = TONES[tone];
  return (
    <span
      className={cn(
        "inline-flex h-[22px] shrink-0 items-center gap-1.5 rounded-pill px-2 text-[12px] leading-4 font-[650] whitespace-nowrap",
        pill,
        className,
      )}
    >
      <span aria-hidden="true" className={cn("size-1.5 rounded-pill", dot)} />
      {label}
    </span>
  );
}

/** Pipeline status. A closed pipeline reads "Completed" when it closed on schedule, "Closed" when closed by hand. */
export function PipelineStatusPill({
  status,
  closedOnSchedule,
  className,
}: {
  status: PipelineStatus;
  closedOnSchedule?: boolean;
  className?: string;
}) {
  const key = status === "closed" && closedOnSchedule ? "completed" : status;
  return (
    <Pill tone={PIPELINE_TONE[status]} label={t(`status.pipeline.${key}`)} className={className} />
  );
}

/** Where an application is. Candidates never see these labels. */
export function StagePill({ stage, className }: { stage: ApplicationStage; className?: string }) {
  return <Pill tone={STAGE_TONE[stage]} label={t(`status.stage.${stage}`)} className={className} />;
}
