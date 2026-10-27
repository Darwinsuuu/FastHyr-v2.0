// New pipeline wizard logic (PIPE-002, PIPE-003): the form for all five steps, how it maps to the
// API's PipelineSetup, and the rules that block Continue and Publish.

import { ApiError, type components } from "@fasthyr/api-client";

import type { MessageKey } from "@/lib/i18n";

export type Pipeline = components["schemas"]["Pipeline"];
export type PipelineSetup = components["schemas"]["PipelineSetup"];
type Department = components["schemas"]["Department"];

export type EmploymentType = NonNullable<PipelineSetup["employment_type"]>;
export type WorkSetup = NonNullable<PipelineSetup["work_setup"]>;
export type OpenTo = NonNullable<PipelineSetup["open_to"]>[number];
export type InterviewFormat = NonNullable<PipelineSetup["interview_format"]>;
export type Tone = NonNullable<PipelineSetup["tone"]>;
export type Seniority = NonNullable<PipelineSetup["seniority"]>;
export type LinkExpiryDays = NonNullable<PipelineSetup["link_expiry_days"]>;
export type OpenMode = NonNullable<PipelineSetup["open_mode"]>;
export type DurationDays = NonNullable<PipelineSetup["duration_days"]>;

export const EMPLOYMENT_TYPES: EmploymentType[] = [
  "full_time",
  "part_time",
  "contract",
  "internship",
];
export const WORK_SETUPS: WorkSetup[] = ["on_site", "hybrid", "remote"];
export const OPEN_TO: OpenTo[] = [
  "fresh_grads",
  "career_changers",
  "returners",
  "no_degree",
  "step_up",
  "relocating",
];
export const FORMATS: InterviewFormat[] = ["video_voice", "voice_only"];
export const TONES: Tone[] = ["warm", "professional", "direct"];
export const SENIORITIES: Seniority[] = ["entry", "mid", "senior", "lead"];
export const LINK_EXPIRY_DAYS: LinkExpiryDays[] = [3, 5, 7, 14];
export const OPEN_MODES: OpenMode[] = ["now", "scheduled"];
export const DURATIONS: DurationDays[] = [30, 60, 90, 120];
export const WEIGHTS = ["weight_technical", "weight_communication", "weight_culture"] as const;
export type WeightKey = (typeof WEIGHTS)[number];

/** Must-haves and skills to probe: at least 3 to continue, at most 20 (the API's limit). */
export const MIN_ITEMS = 3;
export const MAX_ITEMS = 20;
/** Same limits as the API. */
export const TITLE_MAX = 120;
export const LOCATION_MAX = 120;
export const JD_MAX = 20_000;
/** Reserve limits (FR-PIPE-04, the API's ReserveCredits). */
export const RESERVE_MIN = 10;
export const RESERVE_STEP = 10;
const RESERVE_DEFAULT = 100;
/** Pass mark slider range (frame NewPipeline step 3). */
export const PASS_MARK_MIN = 40;
export const PASS_MARK_MAX = 95;
/** The words typed to publish or schedule (FR-PIPE-05; the API checks the same phrase). */
export const CONFIRM_PHRASE = "I understand";

export const STEPS = ["role", "interview", "scoring", "schedule", "review"] as const;
export type StepId = (typeof STEPS)[number];

export interface WizardForm {
  title: string;
  /** null = No department. */
  department_id: string | null;
  employment_type: EmploymentType;
  work_setup: WorkSetup;
  location: string;
  jd_text: string;
  must_haves: string[];
  nice_to_haves: string[];
  open_to: OpenTo[];
  resume_pass_bar: number;
  interview_format: InterviewFormat;
  tone: Tone;
  seniority: Seniority;
  skills_to_probe: string[];
  link_expiry_days: LinkExpiryDays;
  reminder_enabled: boolean;
  integrity_enabled: boolean;
  weight_technical: number;
  weight_communication: number;
  weight_culture: number;
  pass_mark: number;
  email_resume_reject: boolean;
  email_post_interview: boolean;
  open_mode: OpenMode;
  /** The opening date as YYYY-MM-DD (local), "" until picked. Used when open_mode is scheduled. */
  opens_on: string;
  duration_days: DurationDays;
  credits_to_reserve: number;
}

/** 100 credits, or the free credits rounded down to 10s when fewer (never below 10). */
export function defaultReserve(freeCredits: number | null): number {
  if (freeCredits === null) return RESERVE_DEFAULT;
  const affordable = Math.floor(freeCredits / RESERVE_STEP) * RESERVE_STEP;
  return Math.max(RESERVE_MIN, Math.min(RESERVE_DEFAULT, affordable));
}

/** A new pipeline. Lists start empty; numbers and toggles match the API's column defaults. */
export function emptyForm(
  departmentId: string | null,
  freeCredits: number | null = null,
): WizardForm {
  return {
    title: "",
    department_id: departmentId,
    employment_type: "full_time",
    work_setup: "on_site",
    location: "",
    jd_text: "",
    must_haves: [],
    nice_to_haves: [],
    open_to: [],
    resume_pass_bar: 60,
    interview_format: "video_voice",
    tone: "warm",
    seniority: "mid",
    skills_to_probe: [],
    link_expiry_days: 5,
    reminder_enabled: true,
    integrity_enabled: true,
    weight_technical: 50,
    weight_communication: 30,
    weight_culture: 20,
    pass_mark: 70,
    email_resume_reject: true,
    email_post_interview: true,
    open_mode: "now",
    opens_on: "",
    duration_days: 90,
    credits_to_reserve: defaultReserve(freeCredits),
  };
}

const isExpiry = (days: number): days is LinkExpiryDays =>
  (LINK_EXPIRY_DAYS as number[]).includes(days);
const isDuration = (days: number | null): days is DurationDays =>
  days !== null && (DURATIONS as number[]).includes(days);

const pad = (n: number) => String(n).padStart(2, "0");
/** A Date as local YYYY-MM-DD. */
export function isoDay(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}
/** Local midnight at the start of a YYYY-MM-DD day. */
export function startOfDay(day: string): Date {
  const [year = 0, month = 1, date = 1] = day.split("-").map(Number);
  return new Date(year, month - 1, date);
}
/** The earliest opening date: tomorrow (the API needs a time in the future). */
export function firstOpeningDay(now: Date = new Date()): string {
  return isoDay(new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1));
}

/** A saved draft back in the form; choices it never set keep the new-pipeline defaults. */
export function formFromPipeline(pipeline: Pipeline): WizardForm {
  const defaults = emptyForm(pipeline.department_id);
  return {
    ...defaults,
    title: pipeline.title ?? "",
    employment_type: pipeline.employment_type ?? defaults.employment_type,
    work_setup: pipeline.work_setup ?? defaults.work_setup,
    location: pipeline.location ?? "",
    jd_text: pipeline.jd_text ?? "",
    must_haves: pipeline.must_haves,
    nice_to_haves: pipeline.nice_to_haves,
    open_to: pipeline.open_to,
    resume_pass_bar: pipeline.resume_pass_bar,
    interview_format: pipeline.interview_format ?? defaults.interview_format,
    tone: pipeline.tone ?? defaults.tone,
    seniority: pipeline.seniority ?? defaults.seniority,
    skills_to_probe: pipeline.skills_to_probe,
    link_expiry_days: isExpiry(pipeline.link_expiry_days)
      ? pipeline.link_expiry_days
      : defaults.link_expiry_days,
    reminder_enabled: pipeline.reminder_enabled,
    integrity_enabled: pipeline.integrity_enabled,
    weight_technical: pipeline.weight_technical ?? defaults.weight_technical,
    weight_communication: pipeline.weight_communication ?? defaults.weight_communication,
    weight_culture: pipeline.weight_culture ?? defaults.weight_culture,
    pass_mark: pipeline.pass_mark,
    email_resume_reject: pipeline.email_resume_reject,
    email_post_interview: pipeline.email_post_interview,
    open_mode: pipeline.open_mode ?? defaults.open_mode,
    opens_on: pipeline.opens_at ? isoDay(new Date(pipeline.opens_at)) : "",
    duration_days: isDuration(pipeline.duration_days)
      ? pipeline.duration_days
      : defaults.duration_days,
    credits_to_reserve: pipeline.credits_to_reserve ?? defaults.credits_to_reserve,
  };
}

const text = (value: string) => value.trim() || null;

export function weightsTotal(form: Pick<WizardForm, WeightKey>): number {
  return WEIGHTS.reduce((total, key) => total + form[key], 0);
}

/**
 * The request body for POST/PATCH /v1/pipelines, empty text as null. Weights are left out until
 * they add up to 100 (the API refuses any other total), so a draft always saves. A scheduled
 * pipeline keeps its open mode and reserve (Start now and top-up change those), so they're left
 * out too.
 */
export function setupFromForm(
  form: WizardForm,
  { scheduled = false }: { scheduled?: boolean } = {},
): PipelineSetup {
  const { opens_on, weight_technical, weight_communication, weight_culture, ...rest } = form;
  const body: PipelineSetup = {
    ...rest,
    title: text(form.title),
    location: text(form.location),
    jd_text: text(form.jd_text),
    opens_at:
      form.open_mode === "scheduled" && opens_on ? startOfDay(opens_on).toISOString() : null,
  };
  if (weightsTotal(form) === 100) {
    Object.assign(body, { weight_technical, weight_communication, weight_culture });
  }
  if (scheduled) {
    delete body.open_mode;
    delete body.credits_to_reserve;
  }
  return body;
}

/** Why Continue is blocked on `step` (0-based), or null when it isn't. */
export function blockedHint(form: WizardForm, step: number): MessageKey | null {
  if (STEPS[step] === "role" && form.must_haves.length < MIN_ITEMS) {
    return "pipelines.wizard.blocked.mustHaves";
  }
  if (STEPS[step] === "interview" && form.skills_to_probe.length < MIN_ITEMS) {
    return "pipelines.wizard.blocked.skills";
  }
  if (STEPS[step] === "scoring" && weightsTotal(form) !== 100) {
    return "pipelines.wizard.blocked.weights";
  }
  return null;
}

/** Required details that are still empty, so Review can show "Not set" (FR-PIPE-01). */
export function missingDetails(form: WizardForm): Set<"title" | "location" | "jd_text"> {
  const missing = new Set<"title" | "location" | "jd_text">();
  if (!form.title.trim()) missing.add("title");
  if (form.work_setup !== "remote" && !form.location.trim()) missing.add("location");
  if (!form.jd_text.trim()) missing.add("jd_text");
  return missing;
}

/**
 * Why Publish (or Save changes on a scheduled pipeline) is blocked, or null. Mirrors what the
 * API refuses: missing details, the min-3 rules, weights, a past opening date and a reserve
 * bigger than the free credits (`freeCredits` null = not loaded yet, so not checked).
 */
export function publishBlock(
  form: WizardForm,
  freeCredits: number | null,
  { scheduled = false, now = new Date() }: { scheduled?: boolean; now?: Date } = {},
): MessageKey | null {
  if (form.must_haves.length < MIN_ITEMS) return "pipelines.wizard.blocked.mustHaves";
  if (form.skills_to_probe.length < MIN_ITEMS) return "pipelines.wizard.blocked.skills";
  if (weightsTotal(form) !== 100) return "pipelines.wizard.blocked.weights";
  if (missingDetails(form).size > 0) return "pipelines.wizard.blocked.details";
  if (form.open_mode === "scheduled" && (!form.opens_on || form.opens_on < firstOpeningDay(now))) {
    return "pipelines.wizard.blocked.openingDate";
  }
  if (!scheduled && freeCredits !== null && form.credits_to_reserve > freeCredits) {
    return "pipelines.wizard.blocked.credits";
  }
  return null;
}

/** When the pipeline closes: its opening day (today when it opens now) plus the duration. */
export function closeDate(form: WizardForm, now: Date = new Date()): Date {
  const opens =
    form.open_mode === "scheduled" && form.opens_on
      ? startOfDay(form.opens_on)
      : new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return new Date(opens.getFullYear(), opens.getMonth(), opens.getDate() + form.duration_days);
}

export interface DepartmentOption {
  /** The department id, or NO_DEPARTMENT. */
  value: string;
  label: string;
}

/** The Select value for No department (Radix Select can't use an empty string). */
export const NO_DEPARTMENT = "none";

/**
 * Where a pipeline can be filed: Admins pick any department or No department; Recruiters only
 * their own departments (the API refuses the rest with `unknown_department`).
 */
export function departmentOptions(
  departments: Pick<Department, "id" | "name" | "assigned">[],
  isAdmin: boolean,
  noDepartmentLabel: string,
): DepartmentOption[] {
  const options = departments
    .filter((department) => isAdmin || department.assigned)
    .map((department) => ({ value: department.id, label: department.name }));
  return isAdmin ? [{ value: NO_DEPARTMENT, label: noDepartmentLabel }, ...options] : options;
}

/** The department a new pipeline starts in: No department for Admins, else their first one. */
export function defaultDepartment(options: DepartmentOption[], isAdmin: boolean): string | null {
  if (isAdmin) return null;
  return options[0]?.value ?? null;
}

/** The message for a failed save. */
export function saveErrorKey(error: unknown): MessageKey {
  if (error instanceof ApiError) {
    if (error.code === "pipeline_locked") return "pipelines.wizard.errors.locked";
    if (error.code === "unknown_department") return "pipelines.wizard.errors.department";
    if (error.code === "pipeline_incomplete") return "pipelines.wizard.errors.incomplete";
  }
  return "pipelines.wizard.errors.saveFailed";
}

/** The message for a failed publish. */
export function publishErrorKey(error: unknown): MessageKey {
  if (error instanceof ApiError) {
    if (error.code === "insufficient_free_credits") return "pipelines.wizard.errors.credits";
    if (error.code === "pipeline_incomplete") return "pipelines.wizard.errors.incomplete";
    if (error.code === "invalid_transition") return "pipelines.wizard.errors.alreadyPublished";
  }
  return "pipelines.wizard.errors.publishFailed";
}

/** The 8 places a TA team posts the apply link (FR-PIPE-10); the id is the `?source=` tag. */
export const SHARE_SOURCES = [
  "linkedin",
  "jobstreet",
  "indeed",
  "kalibrr",
  "glassdoor",
  "facebook",
  "careers",
  "other",
] as const;
export type ShareSource = (typeof SHARE_SOURCES)[number];

/** `{site}/apply/{workspace-slug}/{pipeline-slug}?source={id}` (FR-PIPE-10). */
export function applyLink(
  siteUrl: string,
  workspaceSlug: string,
  pipelineSlug: string,
  source: ShareSource,
): string {
  const url = new URL(
    `/apply/${encodeURIComponent(workspaceSlug)}/${encodeURIComponent(pipelineSlug)}`,
    siteUrl,
  );
  url.searchParams.set("source", source);
  return url.toString();
}

/** Every source's apply link, for `ShareTiles` where the pipeline was just published. */
export function applyLinks(
  siteUrl: string,
  workspaceSlug: string,
  pipelineSlug: string,
): Record<ShareSource, string> {
  return Object.fromEntries(
    SHARE_SOURCES.map((source) => [
      source,
      applyLink(siteUrl, workspaceSlug, pipelineSlug, source),
    ]),
  ) as Record<ShareSource, string>;
}

/** Drafts and scheduled pipelines (until they open) can still be edited (WORKFLOW.md §2). */
export function isEditable(pipeline: Pick<Pipeline, "status">): boolean {
  return pipeline.status === "draft" || pipeline.status === "scheduled";
}

/** "a", "a or b", "a, b or c" for the Also open to note. */
export function joinWithOr(items: string[], or: string): string {
  if (items.length <= 1) return items[0] ?? "";
  return `${items.slice(0, -1).join(", ")} ${or} ${items[items.length - 1]}`;
}
