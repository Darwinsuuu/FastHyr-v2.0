"use client";

import {
  ArchiveIcon,
  CopyIcon,
  DotsThreeVerticalIcon,
  DownloadSimpleIcon,
  FunnelIcon,
  PauseIcon,
  PencilSimpleIcon,
  PlusIcon,
  TrashIcon,
} from "@phosphor-icons/react";
import { type ReactNode, useEffect, useRef, useState } from "react";

import { Avatar, WorkspaceAvatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button, IconButton } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ChipInput } from "@/components/ui/chip-input";
import { ConfirmDialog, Dialog, TypeToConfirmDialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { FileDrop } from "@/components/ui/file-drop";
import { Input, SearchInput, Textarea } from "@/components/ui/input";
import { JobProgressDialog } from "@/components/ui/job-progress-dialog";
import { Menu } from "@/components/ui/menu";
import { NumberStepper } from "@/components/ui/number-stepper";
import { PhoneInput, type PhoneValue } from "@/components/ui/phone-input";
import { Popover } from "@/components/ui/popover";
import { SegmentedControl } from "@/components/ui/segmented-control";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Slider } from "@/components/ui/slider";
import {
  type ApplicationStage,
  PipelineStatusPill,
  type PipelineStatus,
  StagePill,
} from "@/components/ui/status-pill";
import { Tabs } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";
import { Toggle } from "@/components/ui/toggle";

// Developer-only page: copy here is sample content, not product copy, so it isn't in messages/en.json.

type Theme = "system" | "light" | "dark";

const PIPELINE_STATUSES: PipelineStatus[] = [
  "draft",
  "scheduled",
  "live",
  "paused",
  "paused_no_credits",
  "closed",
  "cancelled",
];
const STAGES: ApplicationStage[] = [
  "processing_resume",
  "resume_not_match",
  "invited",
  "interview_in_progress",
  "scoring",
  "ready_for_review",
  "did_not_pass",
  "advanced",
  "rejected",
];

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="border-t border-line py-8 md:py-10">
      <h2 id={id} className="mb-5 type-heading">
        {title}
      </h2>
      <div className="flex flex-col gap-6">{children}</div>
    </section>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="type-label text-ink-muted">{label}</p>
      <div className="flex flex-wrap items-center gap-3">{children}</div>
    </div>
  );
}

function ThemeSwitch() {
  const [theme, setTheme] = useState<Theme>("system");
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") delete root.dataset.theme;
    else root.dataset.theme = theme;
  }, [theme]);
  return (
    <SegmentedControl
      label="Theme"
      size="sm"
      value={theme}
      onValueChange={setTheme}
      options={[
        { value: "system", label: "System" },
        { value: "light", label: "Paper" },
        { value: "dark", label: "Night" },
      ]}
    />
  );
}

function Actions() {
  return (
    <Section id="actions" title="Actions">
      {(["ta", "candidate"] as const).map((side) => (
        <Row key={side} label={side === "ta" ? "Hiring side" : "Candidate side"}>
          <Button side={side}>Primary</Button>
          <Button side={side} variant="secondary">
            Secondary
          </Button>
          <Button side={side} variant="quiet">
            Quiet
          </Button>
          <Button side={side} loading>
            Saving
          </Button>
          <Button side={side} disabled>
            Disabled
          </Button>
        </Row>
      ))}
      <Row label="Sizes and icons">
        <Button size="sm" icon={<PlusIcon className="size-4" />}>
          New pipeline
        </Button>
        <Button size="md" variant="secondary" icon={<DownloadSimpleIcon className="size-5" />}>
          Export
        </Button>
        <Button size="lg">Continue</Button>
      </Row>
      <Row label="Destructive">
        <Button destructive>Delete workspace</Button>
        <Button destructive variant="secondary">
          Remove member
        </Button>
        <Button destructive variant="quiet">
          Cancel pipeline
        </Button>
      </Row>
      <Row label="Icon buttons (tooltip on hover, focus and tap)">
        <IconButton label="Edit" icon={<PencilSimpleIcon className="size-5" />} />
        <IconButton label="Filter" icon={<FunnelIcon className="size-5" />} />
        <IconButton label="Copy apply link" size="sm" icon={<CopyIcon className="size-5" />} />
      </Row>
    </Section>
  );
}

function Forms() {
  const [skills, setSkills] = useState(["SQL", "Stakeholder management"]);
  const [phone, setPhone] = useState<PhoneValue>({ country: "PH", number: "" });
  const [file, setFile] = useState<File | null>(null);
  const [weight, setWeight] = useState(30);
  const [credits, setCredits] = useState(50);
  const [setup, setSetup] = useState<"onsite" | "hybrid" | "remote">("hybrid");

  return (
    <Section id="forms" title="Forms">
      <div className="grid gap-6 md:grid-cols-2">
        <Field label="Role title" hint="Shown to candidates on the apply page." required>
          <Input placeholder="Senior data analyst" />
        </Field>
        <Field label="Work email" error="Enter an email address like name@company.com.">
          <Input type="email" defaultValue="darwin@" />
        </Field>
        <Field label="Department">
          <Select
            placeholder="Choose a department"
            options={[
              { value: "eng", label: "Engineering" },
              { value: "ops", label: "Operations" },
              { value: "fin", label: "Finance" },
              { value: "none", label: "No department", disabled: true },
            ]}
          />
        </Field>
        <Field label="Search" hideLabel>
          <SearchInput placeholder="Search candidates" />
        </Field>
        <Field
          label="About the role"
          hint="Two or three sentences are enough."
          className="md:col-span-2"
        >
          <Textarea placeholder="What this person will own in their first six months" />
        </Field>
        <Field label="Must-haves" hint="Press Enter or comma to add. Up to 8.">
          <ChipInput
            value={skills}
            onValueChange={setSkills}
            max={8}
            placeholder="Add a must-have"
          />
        </Field>
        <Field label="Phone number">
          <PhoneInput value={phone} onValueChange={setPhone} />
        </Field>
        <Field
          label={`Weight: ${weight}%`}
          hint="How much this criterion counts toward the overall score."
        >
          <Slider
            value={weight}
            onValueChange={setWeight}
            step={5}
            formatValue={(v) => `${v} percent`}
          />
        </Field>
        <Field label="Credits to buy" hint="Between 10 and 1,000, in steps of 10.">
          <NumberStepper
            value={credits}
            onValueChange={setCredits}
            min={10}
            max={1000}
            step={10}
            unit="credits"
          />
        </Field>
        <Field label="Résumé" className="md:col-span-2">
          <FileDrop
            accept={["application/pdf"]}
            maxSize={10 * 1024 * 1024}
            file={file}
            onFileChange={setFile}
            hint="PDF, up to 10 MB"
          />
        </Field>
      </div>
      <Row label="Work setup">
        <SegmentedControl
          label="Work setup"
          value={setup}
          onValueChange={setSetup}
          options={[
            { value: "onsite", label: "On-site" },
            { value: "hybrid", label: "Hybrid" },
            { value: "remote", label: "Remote" },
          ]}
        />
      </Row>
      <div className="grid gap-2 md:max-w-md">
        <Checkbox
          label="Email candidates who don't pass"
          description="Sent 3 business days after the interview."
          defaultChecked
        />
        <Checkbox label="Select all" checked="indeterminate" />
        <Checkbox label="Disabled option" disabled />
        <Toggle
          label="Video interviews"
          description="Candidates can choose voice only."
          defaultChecked
        />
        <Toggle label="Weekly summary email" />
      </div>
    </Section>
  );
}

function Overlays() {
  const toast = useToast();
  const [dialog, setDialog] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [typed, setTyped] = useState(false);
  const [job, setJob] = useState(false);
  const started = useRef(0);

  return (
    <Section id="overlays" title="Overlays">
      <Row label="Dialogs (full-screen sheet on phones)">
        <Button variant="secondary" onClick={() => setDialog(true)}>
          Open dialog
        </Button>
        <Button variant="secondary" onClick={() => setConfirm(true)}>
          Confirm dialog
        </Button>
        <Button variant="secondary" destructive onClick={() => setTyped(true)}>
          Type to confirm
        </Button>
        <Button
          variant="secondary"
          onClick={() => {
            started.current = Date.now();
            setJob(true);
          }}
        >
          Job progress
        </Button>
      </Row>
      <Row label="Menu (bottom sheet on phones), popover, toast">
        <Menu
          title="Senior data analyst"
          trigger={
            <IconButton label="More actions" icon={<DotsThreeVerticalIcon className="size-5" />} />
          }
          items={[
            {
              label: "Edit",
              icon: <PencilSimpleIcon />,
              onSelect: () => toast({ title: "Edit chosen" }),
            },
            {
              label: "Duplicate as new pipeline",
              icon: <CopyIcon />,
              onSelect: () => toast({ title: "Duplicated" }),
            },
            {
              label: "Pause",
              icon: <PauseIcon />,
              onSelect: () => toast({ title: "Pipeline paused" }),
            },
            "separator",
            { label: "Archive", icon: <ArchiveIcon />, onSelect: () => undefined, disabled: true },
            {
              label: "Cancel pipeline",
              icon: <TrashIcon />,
              destructive: true,
              onSelect: () => setConfirm(true),
            },
          ]}
        />
        <Popover trigger={<Button variant="secondary">Filters</Button>}>
          <p className="mb-3 text-[14px] font-semibold">Show candidates</p>
          <Checkbox label="Ready for review" defaultChecked />
          <Checkbox label="Flagged" />
        </Popover>
        <Button
          variant="secondary"
          onClick={() =>
            toast({
              title: "Member removed",
              description: "They no longer have access.",
              action: { label: "Undo", onClick: () => undefined },
            })
          }
        >
          Show toast
        </Button>
        <Button
          variant="secondary"
          onClick={() => toast({ title: "We couldn't save that change.", tone: "error" })}
        >
          Error toast
        </Button>
      </Row>
      <Tabs
        label="Pipeline sections"
        items={[
          {
            value: "overview",
            label: "Overview",
            content: <p className="text-ink-muted">Overview content.</p>,
          },
          {
            value: "candidates",
            label: "Candidates",
            count: 128,
            content: <p className="text-ink-muted">Candidates content.</p>,
          },
          {
            value: "questions",
            label: "Questions",
            content: <p className="text-ink-muted">Questions content.</p>,
          },
          {
            value: "scoring",
            label: "Scoring rubric",
            content: <p className="text-ink-muted">Scoring content.</p>,
          },
          {
            value: "settings",
            label: "Settings",
            content: <p className="text-ink-muted">Settings content.</p>,
          },
        ]}
      />

      <Dialog
        open={dialog}
        onOpenChange={setDialog}
        title="Invite a teammate"
        description="They'll get an email with a link to join Acme."
        footer={
          <>
            <Button variant="secondary" onClick={() => setDialog(false)}>
              Cancel
            </Button>
            <Button onClick={() => setDialog(false)}>Send invite</Button>
          </>
        }
      >
        <div className="flex flex-col gap-5">
          <Field label="Work email">
            <Input type="email" placeholder="name@company.com" />
          </Field>
          <Field label="Role">
            <Select
              defaultValue="recruiter"
              options={[
                { value: "admin", label: "Admin" },
                { value: "recruiter", label: "Recruiter" },
                { value: "hiring_manager", label: "Hiring manager" },
              ]}
            />
          </Field>
        </div>
      </Dialog>
      <ConfirmDialog
        open={confirm}
        onOpenChange={setConfirm}
        title="Close this pipeline?"
        description="The apply link stops taking applications. Candidates already in the pipeline keep their interviews and results, and unused credits return to your balance."
        confirmLabel="Close pipeline"
        onConfirm={() => new Promise((resolve) => setTimeout(resolve, 800))}
      />
      <TypeToConfirmDialog
        open={typed}
        onOpenChange={setTyped}
        title="Delete Acme workspace?"
        description="This deletes every pipeline, candidate and report in Acme. It can't be undone."
        phrase="I understand"
        confirmLabel="Delete workspace"
        onConfirm={() => undefined}
      />
      <JobProgressDialog
        open={job}
        onOpenChange={setJob}
        title="Preparing your report"
        description="We're building the PDF with every candidate's scores."
        poll={async () => {
          const progress = Math.min(100, Math.round((Date.now() - started.current) / 60));
          return progress >= 100
            ? { state: "succeeded", progress }
            : { state: "running", progress };
        }}
        onSucceeded={() => {
          setJob(false);
          toast({ title: "Report ready", description: "Your download has started." });
        }}
        intervalMs={300}
      />
    </Section>
  );
}

function Feedback() {
  return (
    <Section id="feedback" title="Feedback">
      <Row label="Skeleton">
        <div
          aria-busy="true"
          aria-label="Loading"
          className="flex w-full max-w-md flex-col gap-3 rounded-md border border-line p-4"
        >
          <Skeleton className="h-5 w-1/2" />
          <Skeleton className="w-full" />
          <Skeleton className="w-4/5" />
        </div>
      </Row>
      <div className="rounded-md border border-line">
        <EmptyState
          title="No pipelines yet"
          description="Create a pipeline for a role, then paste its apply link into your job posts."
          action={<Button icon={<PlusIcon className="size-5" />}>New pipeline</Button>}
        />
      </div>
    </Section>
  );
}

function Identity() {
  const people = [
    { id: "u1", name: "Maria Santos" },
    { id: "u2", name: "Jon Reyes" },
    { id: "u3", name: "Ana" },
    { id: "u4", name: "Kai Tanaka Cruz" },
  ];
  return (
    <Section id="identity" title="Identity and status">
      <Row label="Avatars">
        {people.map((person) => (
          <span key={person.id} className="flex items-center gap-2 text-[14px]">
            <Avatar id={person.id} name={person.name} />
            {person.name}
          </span>
        ))}
        <Avatar id="u5" name="Small Size" size="sm" />
        <Avatar id="u6" name="Large Size" size="lg" />
        <WorkspaceAvatar name="Acme Corp" />
      </Row>
      <Row label="Badges">
        <Badge>Owner</Badge>
        <Badge tone="evergreen">Admin</Badge>
        <Badge tone="persimmon">Candidate quote</Badge>
        <Badge tone="outline">Trial</Badge>
        <Badge tone="strong">Strong evidence</Badge>
        <Badge tone="watch">Worth probing</Badge>
        <Badge tone="gap">Not evidenced yet</Badge>
      </Row>
      <Row label="Pipeline status">
        {PIPELINE_STATUSES.map((status) => (
          <PipelineStatusPill key={status} status={status} />
        ))}
        <PipelineStatusPill status="closed" closedOnSchedule />
      </Row>
      <Row label="Application stage">
        {STAGES.map((stage) => (
          <StagePill key={stage} stage={stage} />
        ))}
      </Row>
    </Section>
  );
}

/** Every UI kit component with its variants and states. */
export function Gallery() {
  return (
    <main className="page-gutter pb-16">
      <header className="flex flex-col gap-4 py-8 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="type-label text-ink-muted">FND-012 · developer only</p>
          <h1 className="mt-2 type-display-lg">UI kit</h1>
        </div>
        <ThemeSwitch />
      </header>
      <Actions />
      <Forms />
      <Overlays />
      <Feedback />
      <Identity />
    </main>
  );
}
