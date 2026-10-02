// New pipeline wizard logic (PIPE-002): the form for the Role and AI interview steps, how it maps
// to the API's PipelineSetup, and the rules that block Continue.

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

/** Must-haves and skills to probe: at least 3 to continue, at most 20 (the API's limit). */
export const MIN_ITEMS = 3;
export const MAX_ITEMS = 20;
/** Same limits as the API. */
export const TITLE_MAX = 120;
export const LOCATION_MAX = 120;
export const JD_MAX = 20_000;

/** The wizard's steps; PIPE-003 builds Scoring, Schedule & credits and Review. */
export const STEPS = ["role", "interview", "scoring", "schedule", "review"] as const;
export type StepId = (typeof STEPS)[number];
/** Steps this task builds. Later steps show a "coming next" panel. */
export const BUILT_STEPS = 2;

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
}

/** A new pipeline. Lists start empty; numbers and toggles match the API's column defaults. */
export function emptyForm(departmentId: string | null): WizardForm {
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
  };
}

const isExpiry = (days: number): days is LinkExpiryDays =>
  (LINK_EXPIRY_DAYS as number[]).includes(days);

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
  };
}

const text = (value: string) => value.trim() || null;

/** The request body for POST/PATCH /v1/pipelines: every field of steps 1–2, empty text as null. */
export function setupFromForm(form: WizardForm): PipelineSetup {
  return {
    ...form,
    title: text(form.title),
    location: text(form.location),
    jd_text: text(form.jd_text),
  };
}

/** Why Continue is blocked on `step` (0-based), or null when it isn't. */
export function blockedHint(form: WizardForm, step: number): MessageKey | null {
  if (STEPS[step] === "role" && form.must_haves.length < MIN_ITEMS) {
    return "pipelines.wizard.blocked.mustHaves";
  }
  if (STEPS[step] === "interview" && form.skills_to_probe.length < MIN_ITEMS) {
    return "pipelines.wizard.blocked.skills";
  }
  return null;
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
  }
  return "pipelines.wizard.errors.saveFailed";
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
