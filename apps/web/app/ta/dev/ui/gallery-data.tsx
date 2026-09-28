"use client";

import {
  CopyIcon,
  DotsThreeVerticalIcon,
  EyeIcon,
  PauseIcon,
  XCircleIcon,
} from "@phosphor-icons/react";
import { useState } from "react";

import { BarChart } from "@/components/charts/bar-chart";
import { FlowBand } from "@/components/charts/flow-band";
import { HorizontalBars } from "@/components/charts/horizontal-bars";
import { LineChart } from "@/components/charts/line-chart";
import { RadarChart } from "@/components/charts/radar-chart";
import { SplitBar } from "@/components/charts/split-bar";
import { Button, IconButton } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { InsightCard } from "@/components/ui/insight-card";
import { Menu } from "@/components/ui/menu";
import { Pagination } from "@/components/ui/pagination";
import { QuestionPrompt } from "@/components/ui/question-prompt";
import { ScoreBar } from "@/components/ui/score-bar";
import { SegmentedControl } from "@/components/ui/segmented-control";
import { Signal, SignalCounts } from "@/components/ui/signal";
import { type PipelineStatus, PipelineStatusPill } from "@/components/ui/status-pill";
import { Stepper } from "@/components/ui/stepper";
import { Table } from "@/components/ui/table";
import { WeightedCalc } from "@/components/ui/weighted-calc";
import { pageAfterResize } from "@/lib/pagination";

import { Row, Section } from "./gallery-parts";

// Developer-only sample data; not product copy.

interface SamplePipeline {
  id: string;
  title: string;
  department: string;
  status: PipelineStatus;
  candidates: number;
  toReview: number;
  creditsUsed: number;
  creditsTotal: number;
  daysLeft: string;
}

const TITLES = [
  "Senior data analyst",
  "Customer support lead",
  "Backend engineer",
  "Product designer",
  "Account executive",
  "People partner",
];
const DEPARTMENTS = [
  "Data & Analytics",
  "Customer Support",
  "Engineering",
  "Design",
  "Sales",
  "People",
];
const STATUSES: PipelineStatus[] = [
  "live",
  "live",
  "paused",
  "scheduled",
  "closed",
  "paused_no_credits",
];

const PIPELINES: SamplePipeline[] = Array.from({ length: 42 }, (_, index) => ({
  id: `p${index + 1}`,
  title: `${TITLES[index % TITLES.length]}${index >= TITLES.length ? ` ${Math.floor(index / TITLES.length) + 1}` : ""}`,
  department: DEPARTMENTS[index % DEPARTMENTS.length] ?? "",
  status: STATUSES[index % STATUSES.length] ?? "live",
  candidates: (index * 37) % 180,
  toReview: index % 3 === 0 ? (index % 7) + 1 : 0,
  creditsUsed: (index * 23) % 200,
  creditsTotal: 200,
  daysLeft: index % 4 === 3 ? "Closed" : `${(index % 20) + 2} days`,
}));

function CreditsCell({ used, total }: { used: number; total: number }) {
  const ratio = used / total;
  return (
    <div className="flex w-[150px] flex-col gap-1.5">
      <span className="text-[14px] text-ink-muted">
        <span className="text-[15px] font-[650] text-ink tabular-nums">{used}</span> / {total}
      </span>
      <ScoreBar
        label="Credits used"
        value={used}
        max={total}
        size={6}
        fillClassName={ratio >= 1 ? "bg-signal-gap" : ratio >= 0.8 ? "bg-signal-watch" : undefined}
      />
    </div>
  );
}

function RowMenu({ row }: { row: SamplePipeline }) {
  return (
    <Menu
      title={row.title}
      trigger={
        <IconButton
          label="More actions"
          icon={<DotsThreeVerticalIcon weight="bold" className="size-5" />}
        />
      }
      items={[
        { label: "Open pipeline", icon: <EyeIcon />, onSelect: () => undefined },
        { label: "Copy apply link", icon: <CopyIcon />, onSelect: () => undefined },
        "separator",
        { label: "Pause pipeline", icon: <PauseIcon />, onSelect: () => undefined },
        {
          label: "Close pipeline",
          icon: <XCircleIcon />,
          destructive: true,
          onSelect: () => undefined,
        },
      ]}
    />
  );
}

function DataTableDemo() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [empty, setEmpty] = useState(false);
  const rows = empty ? [] : PIPELINES.slice((page - 1) * pageSize, page * pageSize);

  return (
    <Section id="data" title="Data">
      <Row label="Table (card list below md, lower-priority columns from lg)">
        <SegmentedControl
          label="Table state"
          size="sm"
          value={empty ? "empty" : "rows"}
          onValueChange={(value) => setEmpty(value === "empty")}
          options={[
            { value: "rows", label: "With rows" },
            { value: "empty", label: "Empty" },
          ]}
        />
      </Row>
      <Table
        caption="Pipelines"
        rows={rows}
        rowKey={(row) => row.id}
        empty={
          <EmptyState
            title="No pipelines yet"
            description="Create a pipeline for a role to get its apply link."
            action={<Button>New pipeline</Button>}
          />
        }
        columns={[
          {
            key: "pipeline",
            header: "Pipeline",
            cell: (row) => (
              <div className="flex flex-col gap-1">
                <span className="text-[15px] font-[650]">{row.title}</span>
                <span className="flex flex-wrap items-center gap-2 text-[13px] text-ink-muted">
                  {row.department} <PipelineStatusPill status={row.status} />
                </span>
              </div>
            ),
          },
          {
            key: "candidates",
            header: "Candidates",
            className: "w-[180px]",
            cell: (row) => (
              <span className="flex items-center gap-2">
                <span className="text-[18px] font-[650] tabular-nums">{row.candidates}</span>
                {row.toReview > 0 && (
                  <span className="rounded-[8px] bg-persimmon-soft px-2 py-1 text-[12px] font-bold text-persimmon-ink">
                    {row.toReview} to review
                  </span>
                )}
              </span>
            ),
          },
          {
            key: "credits",
            header: "Credits used",
            showFrom: "lg",
            className: "w-[190px]",
            cell: (row) => <CreditsCell used={row.creditsUsed} total={row.creditsTotal} />,
          },
          {
            key: "days",
            header: "Days remaining",
            showFrom: "xl",
            className: "w-[150px]",
            cell: (row) => row.daysLeft,
          },
        ]}
        card={(row) => (
          <div className="flex flex-col gap-2">
            <span className="text-[15px] font-[650] text-ink">{row.title}</span>
            <span className="flex flex-wrap items-center gap-2 text-[13px] text-ink-muted">
              {row.department} <PipelineStatusPill status={row.status} />
            </span>
            <span className="text-[14px] text-ink-muted">
              <span className="font-[650] text-ink tabular-nums">{row.candidates}</span> candidates
              · <span className="font-[650] text-ink tabular-nums">{row.creditsUsed}</span> /{" "}
              {row.creditsTotal} credits
            </span>
          </div>
        )}
        rowMenu={(row) => <RowMenu row={row} />}
        footer={
          empty ? undefined : (
            <Pagination
              total={PIPELINES.length}
              page={page}
              pageSize={pageSize}
              onPageChange={setPage}
              onPageSizeChange={(size) => {
                setPage(pageAfterResize(page, pageSize, size));
                setPageSize(size);
              }}
              noun="pipelines"
            />
          )
        }
      />
    </Section>
  );
}

function Evidence() {
  return (
    <Section id="evidence" title="Evidence and scores">
      <Row label="Signals (glyph and word, never colour alone)">
        <Signal level="strong" />
        <Signal level="watch" />
        <Signal level="gap" />
        <SignalCounts counts={{ strong: 4, watch: 2, gap: 1 }} />
      </Row>
      <div className="grid max-w-xl gap-4">
        <ScoreBar label="Must-haves" value={100} />
        <ScoreBar label="Overall score" value={91} passMark={70} size={10} />
      </div>
      <div className="rounded-md border border-line bg-surface-raised p-4 md:p-6">
        <h3 className="type-title">How we got to 91</h3>
        <p className="mt-1 mb-4 text-[14px] text-ink-muted">
          Each criterion score is multiplied by the weight you set for this pipeline, then added up.
        </p>
        <WeightedCalc
          passMark={70}
          items={[
            { label: "Technical fit", score: 94, weight: 50 },
            { label: "Communication", score: 88, weight: 30 },
            { label: "Culture alignment", score: 86, weight: 20 },
          ]}
          note="Rubric set on 12 Sep and locked when the pipeline was published."
        />
      </div>
    </Section>
  );
}

function Signature() {
  return (
    <Section id="signature" title="Signature components">
      <div className="grid gap-6 lg:grid-cols-2">
        <InsightCard
          topic="Leadership"
          level="watch"
          excerpt="Led payments migration to event-driven architecture; reduced p95 latency 38% (2024)."
          highlight="Led payments migration"
          finding="Owned a large migration end to end. Team size and how decisions were shared aren't stated."
          question="Walk us through the payments migration. Who was on the team, and what was one call you made that someone disagreed with?"
        />
        <div className="rounded-lg bg-surface p-0 md:p-4">
          <QuestionPrompt
            step={3}
            total={8}
            question="Walk us through the payments migration you led. Who was on the team?"
            context="You mentioned leading a payments migration in 2024. We'd like to hear how it went."
            hint="Take a moment to think. The timer starts when you press Record."
          >
            <Button side="candidate" size="lg">
              Record my answer
            </Button>
            <Button side="candidate" variant="quiet">
              Type instead
            </Button>
          </QuestionPrompt>
        </div>
      </div>
    </Section>
  );
}

function Progress() {
  const [current, setCurrent] = useState(2);
  const steps = [
    { label: "Role", hint: "Job details and must-haves" },
    { label: "AI interview", hint: "Format, tone and skills" },
    { label: "Scoring", hint: "Rubric and messages" },
    { label: "Schedule & credits", hint: "Dates and budget" },
    { label: "Review", hint: "Check and publish" },
  ];
  return (
    <Section id="progress" title="Progress">
      <Row label="Wizard (compact header on phones)">
        <Button
          size="sm"
          variant="secondary"
          disabled={current === 0}
          onClick={() => setCurrent(current - 1)}
        >
          Back
        </Button>
        <Button
          size="sm"
          disabled={current === steps.length - 1}
          onClick={() => setCurrent(current + 1)}
        >
          Continue
        </Button>
      </Row>
      <div className="grid gap-8 md:grid-cols-[280px_1fr]">
        <Stepper
          label="New pipeline steps"
          steps={steps}
          current={current}
          onStepClick={setCurrent}
        />
        <Stepper
          label="Demo steps"
          orientation="horizontal"
          current={1}
          steps={[
            { label: "Job description", hint: "Paste or pick a sample" },
            { label: "Résumé", hint: "Upload a PDF" },
            { label: "Interviewer", hint: "Voice and tone" },
          ]}
        />
      </div>
    </Section>
  );
}

function Charts() {
  const card = "min-w-0 rounded-md border border-line bg-surface-raised p-4 md:p-6";
  return (
    <Section id="charts" title="Charts">
      <div className={card}>
        <h3 className="mb-4 type-title">How candidates are moving</h3>
        <FlowBand
          title="How candidates are moving"
          stages={[
            { label: "Applied", value: 96 },
            { label: "Invited", value: 58, note: "60% of applicants" },
            { label: "Interviewed", value: 41, note: "71% of those invited" },
            { label: "Ready", value: 12, note: "29% of those interviewed" },
          ]}
        />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className={card}>
          <h3 className="mb-4 type-title">Applicants per week</h3>
          <BarChart
            title="Applicants per week"
            series={[
              { name: "Applied", fill: "bg-chart-3" },
              { name: "Passed the interview", fill: "bg-evergreen" },
            ]}
            data={[58, 64, 71, 69, 77, 82, 81, 96].map((applied, index) => ({
              label: index === 7 ? "This week" : `${3 + index * 7} Aug`,
              values: [applied, 5 + index],
            }))}
            phoneLabelEvery={2}
          />
        </div>
        <div className={card}>
          <h3 className="mb-4 type-title">Interview scores</h3>
          <BarChart
            title="Interview scores"
            series={[{ name: "Candidates", fill: "bg-evergreen" }]}
            data={[
              { label: "40s", values: [5] },
              { label: "50s", values: [10] },
              { label: "60s", values: [14] },
              { label: "70s", values: [3] },
              { label: "80s", values: [2] },
              { label: "90+", values: [1] },
            ]}
            fillFor={(_, index) => (index < 3 ? "bg-chart-muted" : undefined)}
            marker={{ beforeIndex: 3, label: "Pass mark" }}
            height={140}
          />
        </div>
        <div className={card}>
          <h3 className="mb-4 type-title">New applicants per day</h3>
          <BarChart
            title="New applicants per day"
            series={[{ name: "Applicants", fill: "bg-evergreen" }]}
            data={[6, 8, 5, 9, 11, 7, 10, 12, 9, 14, 13, 11, 15, 17].map((value, index) => ({
              label: `${index + 15} Sep`,
              values: [value],
            }))}
            showValues={false}
            labelEvery={2}
            phoneLabelEvery={4}
            height={140}
          />
        </div>
        <div className={card}>
          <h3 className="mb-4 type-title">Monthly credit use</h3>
          <BarChart
            title="Monthly credit use"
            mode="stacked"
            max={480}
            series={[
              { name: "Plan", fill: "bg-evergreen" },
              { name: "Extra", fill: "bg-chart-3" },
            ]}
            data={[
              { label: "Apr", values: [150, 0] },
              { label: "May", values: [180, 0] },
              { label: "Jun", values: [260, 0] },
              { label: "Jul", values: [300, 60] },
              { label: "Aug", values: [300, 160] },
              { label: "Sep (so far)", values: [190, 0] },
            ]}
            referenceLine={{ value: 300, label: "300" }}
            height={200}
          />
        </div>
        <div className={card}>
          <h3 className="mb-4 type-title">Where candidates are</h3>
          <HorizontalBars
            title="Where candidates are"
            size={10}
            rows={[
              { label: "Applied", value: 96, fill: "bg-chart-muted" },
              { label: "Invited", value: 58, note: "60%", fill: "bg-chart-3" },
              { label: "Interviewed", value: 41, note: "71%", fill: "bg-chart-2" },
              { label: "Ready", value: 12, note: "29%", fill: "bg-evergreen" },
            ]}
          />
        </div>
        <div className={card}>
          <h3 className="mb-4 type-title">Credits</h3>
          <SplitBar
            title="Credits"
            size={18}
            segments={[
              { label: "Reserved by live pipelines", value: 824, fill: "bg-evergreen" },
              { label: "Reserved by scheduled", value: 120, fill: "bg-chart-3" },
              { label: "Free to use", value: 816, fill: "bg-chart-amber" },
            ]}
          />
        </div>
        <div className={card}>
          <h3 className="mb-4 type-title">Interview topic scores</h3>
          <RadarChart
            title="Interview topic scores"
            axes={[
              "System design",
              "Data modelling",
              "Communication",
              "Ownership",
              "Collaboration",
              "Problem solving",
            ]}
            series={[
              { name: "Bea", values: [92, 88, 86, 95, 84, 90], variant: "primary" },
              { name: "Pipeline average", values: [70, 66, 72, 64, 75, 68], variant: "comparison" },
            ]}
          />
        </div>
        <div className={card}>
          <h3 className="mb-4 type-title">History with Acme Talent</h3>
          <LineChart
            title="History with Acme Talent"
            points={[
              { label: "Mar 2025", value: 64 },
              { label: "Nov 2025", value: 79 },
              { label: "Sep 2026", value: 91 },
            ]}
            passMark={70}
            passMarkLabel="Pass mark 70"
          />
        </div>
      </div>
    </Section>
  );
}

/** Part 2 of the UI kit: data, evidence, signature pieces, progress and charts. */
export function DataSections() {
  return (
    <>
      <DataTableDemo />
      <Evidence />
      <Signature />
      <Progress />
      <Charts />
    </>
  );
}
