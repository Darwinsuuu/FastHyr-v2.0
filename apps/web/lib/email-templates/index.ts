// Email templates (MSG-002, frames EmailTemplates and EditEmailTemplate + A-07): what each
// template is for, the filters, parameter chips in the editor, change history wording and the
// checks the API also makes on save.

import type { components } from "@fasthyr/api-client";

export type EmailTemplate = components["schemas"]["EmailTemplate"];
export type EmailTemplateSummary = components["schemas"]["EmailTemplateSummary"];
export type EmailTemplateVersion = components["schemas"]["EmailTemplateVersion"];
export type TemplateKey = EmailTemplateSummary["key"];

/** The label on each card and in the editor header. */
export type TemplateCategory =
  "invitation" | "reminder" | "confirmation" | "advancement" | "rejection" | "update";

/** The filter chips: confirmations sit with the updates (A-07 adds only "Updates"). */
export type TemplateFilter =
  "all" | "invitations" | "reminders" | "advancement" | "rejections" | "updates";

export const FILTERS: readonly TemplateFilter[] = [
  "all",
  "invitations",
  "reminders",
  "advancement",
  "rejections",
  "updates",
];

/** In the API's order (NOTIFICATIONS.md §1). */
export const TEMPLATE_KEYS: readonly TemplateKey[] = [
  "interview_invitation",
  "interview_reminder",
  "finish_interview",
  "interview_received",
  "next_stage",
  "reject_resume",
  "reject_interview",
  "role_closed",
  "review_received",
  "review_upheld",
];

export const CATEGORY: Record<TemplateKey, TemplateCategory> = {
  interview_invitation: "invitation",
  interview_reminder: "reminder",
  finish_interview: "reminder",
  interview_received: "confirmation",
  next_stage: "advancement",
  reject_resume: "rejection",
  reject_interview: "rejection",
  role_closed: "update",
  review_received: "update",
  review_upheld: "update",
};

const FILTER_OF: Record<TemplateCategory, Exclude<TemplateFilter, "all">> = {
  invitation: "invitations",
  reminder: "reminders",
  confirmation: "updates",
  advancement: "advancement",
  rejection: "rejections",
  update: "updates",
};

export function isTemplateKey(value: string): value is TemplateKey {
  return (TEMPLATE_KEYS as readonly string[]).includes(value);
}

export function matchesFilter(key: TemplateKey, filter: TemplateFilter): boolean {
  return filter === "all" || FILTER_OF[CATEGORY[key]] === filter;
}

export function filterCounts(keys: readonly TemplateKey[]): Record<TemplateFilter, number> {
  const counts = Object.fromEntries(FILTERS.map((filter) => [filter, 0])) as Record<
    TemplateFilter,
    number
  >;
  for (const key of keys) {
    counts.all += 1;
    counts[FILTER_OF[CATEGORY[key]]] += 1;
  }
  return counts;
}

// Parameters ------------------------------------------------------------------------------

/** Same shape as the API's: `[Candidate.firstname]`. */
export const PARAMETER = /\[([A-Za-z]+\.[A-Za-z]+)\]/g;
/** Anything written like a parameter, to catch typos such as `[Candidate.first_name]`. */
const PARAMETER_LIKE = /\[([^[\]<>\n]{1,60}\.[^[\]<>\n]{1,60})\]/g;

/** The review line every rejection ends with (ADR-015); the editor shows it locked. */
export const REVIEW_LINK = "Review.link";

/** What can be inserted: the review link is always added for rejections, so it isn't offered. */
export function insertable(parameters: readonly string[]): string[] {
  return parameters.filter((name) => name !== REVIEW_LINK);
}

/** Parameters in `text` this template can't fill, as written, each once. */
export function unknownParameters(text: string, allowed: readonly string[]): string[] {
  const found: string[] = [];
  for (const match of text.matchAll(PARAMETER_LIKE)) {
    if (!allowed.includes(match[1] ?? "") && !found.includes(match[0])) found.push(match[0]);
  }
  return found;
}

/** Whether the body already has the review link, so the locked line isn't shown twice. */
export function hasReviewLink(html: string): boolean {
  return html.includes(`[${REVIEW_LINK}]`);
}

/** The stored HTML with each parameter in text wrapped as a chip the editor reads. Parameters
 * inside attributes (a link to `[Interview.link]`) stay as they are. */
export function withParameterChips(html: string): string {
  return html
    .split(/(<[^>]*>)/)
    .map((part) =>
      part.startsWith("<")
        ? part
        : part.replace(
            PARAMETER,
            (whole, name: string) => `<span data-parameter="${name}">${whole}</span>`,
          ),
    )
    .join("");
}

/** True when the message has words in it, not just empty paragraphs or chips' spacing. */
export function hasText(html: string): boolean {
  return (
    html
      .replace(/<[^>]*>/g, "")
      .replace(/&nbsp;/g, " ")
      .trim().length > 0
  );
}

export const SUBJECT_MAX = 200;

export type FieldProblem = { field: "subject" | "body_html"; kind: string; parameter?: string };

/** The checks the API makes on save, so the editor can say what's wrong before sending. */
export function problems(
  subject: string,
  bodyHtml: string,
  allowed: readonly string[],
): FieldProblem[] {
  const found: FieldProblem[] = [];
  const cleaned = subject.trim();
  if (!cleaned) found.push({ field: "subject", kind: "missing" });
  else if (cleaned.length > SUBJECT_MAX) found.push({ field: "subject", kind: "too_long" });
  if (!hasText(bodyHtml)) found.push({ field: "body_html", kind: "missing" });
  for (const [field, text] of [
    ["subject", subject],
    ["body_html", bodyHtml],
  ] as const) {
    for (const parameter of unknownParameters(text, allowed)) {
      found.push({ field, kind: "unknown_parameter", parameter });
    }
  }
  return found;
}

/** The API's `422 email_template_invalid` errors in the same shape. */
export function apiProblems(errors: unknown): FieldProblem[] {
  if (!Array.isArray(errors)) return [];
  return errors.flatMap((error: { loc?: unknown[]; type?: string; msg?: string }) => {
    const field = error.loc?.at(-1);
    if (field !== "subject" && field !== "body_html") return [];
    return [
      {
        field,
        kind: error.type ?? "invalid",
        parameter: error.type === "unknown_parameter" ? error.msg : undefined,
      },
    ];
  });
}

// "Send test to me" ------------------------------------------------------------------------

export const SAMPLE = {
  firstName: "Bea",
  lastName: "Garcia",
  jobTitle: "Senior Backend Engineer",
};

/** The subject as the test email will have it, with the sample details filled in. */
export function sampleSubject(subject: string, company: string): string {
  const values: Record<string, string> = {
    "Candidate.firstname": SAMPLE.firstName,
    "Candidate.lastname": SAMPLE.lastName,
    "Job.title": SAMPLE.jobTitle,
    "Company.name": company,
  };
  return subject.replace(PARAMETER, (whole, name: string) => values[name] ?? whole);
}

// Change history ---------------------------------------------------------------------------

export type ChangeKind =
  "edited_both" | "edited_subject" | "edited_message" | "reset" | "restored" | "saved";

/** What a version changed, compared with the one before it (versions come newest first). */
export function changeOf(versions: readonly EmailTemplateVersion[], index: number): ChangeKind {
  const version = versions[index];
  if (!version) return "saved";
  if (version.kind === "reset") return "reset";
  if (version.kind === "restore") return "restored";
  const previous = versions[index + 1];
  if (!previous) return "saved";
  const subject = previous.subject !== version.subject;
  const body = previous.body_html !== version.body_html;
  if (subject && body) return "edited_both";
  if (subject) return "edited_subject";
  if (body) return "edited_message";
  return "saved";
}

/** The editor's HTML with each chip back to plain `[Parameter]` text, as the API stores it. */
export function withoutParameterChips(html: string): string {
  return html.replace(/<span\b[^>]*\bdata-parameter="[^"]*"[^>]*>([^<]*)<\/span>/g, "$1");
}

/** A web or email address for a link, or null when it isn't one. A bare domain gets https://
 * and a bare email address gets mailto:. */
export function linkHref(input: string): string | null {
  const value = input.trim();
  if (!value || /\s/.test(value)) return null;
  if (/^(https?:\/\/|mailto:)\S+$/i.test(value)) return value;
  if (/^[^@/]+@[^@/]+\.[^@/]+$/.test(value)) return `mailto:${value}`;
  if (/^[\w-]+(\.[\w-]+)+(\/\S*)?$/.test(value)) return `https://${value}`;
  return null;
}
