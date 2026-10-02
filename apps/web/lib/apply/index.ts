// Public apply page logic (APPLY-001): the source tag, the job description layout and the
// status line candidates see.

import type { components } from "@fasthyr/api-client";

import { formatDayLong } from "@/lib/format";
import { t } from "@/lib/i18n";

export type PublicPipeline = components["schemas"]["PublicPipeline"];
export type Availability = PublicPipeline["availability"];
/** The signed-in candidate's own application (`my-application`, APPLY-003/004). */
export type MyApplication = components["schemas"]["MyApplication"];
export type CandidateStatus = NonNullable<MyApplication["status"]>;

// The page is rendered on the server, which doesn't know the reader's locale; dates follow the
// design ("Fri, 26 Feb 2027") in the employer's time zone.
const DATE_LOCALE = "en-GB";

export function applyDate(value: string, timeZone: string): string {
  return formatDayLong(value, timeZone, DATE_LOCALE);
}

// Source tags (GLOSSARY.md): the share tiles add one to every apply link (PIPE-003/006).
export const SOURCE_TAGS = [
  "linkedin",
  "jobstreet",
  "indeed",
  "kalibrr",
  "glassdoor",
  "facebook",
  "careers",
  "other",
] as const;
export type SourceTag = (typeof SOURCE_TAGS)[number] | "direct";

/** A known `?source=` value, or "direct" for none or anything else. */
export function parseSource(value: string | string[] | null | undefined): SourceTag {
  const first = Array.isArray(value) ? value[0] : value;
  const tag = first?.trim().toLowerCase();
  return (SOURCE_TAGS as readonly string[]).includes(tag ?? "") ? (tag as SourceTag) : "direct";
}

const sourceKey = (workspaceSlug: string, pipelineSlug: string) =>
  `fh_apply_source:${workspaceSlug}/${pipelineSlug}`;

/**
 * Keeps the tag the candidate arrived with for this pipeline, so it survives the sign-in round
 * trip (APPLY-002) even if the return URL loses it. "direct" never replaces a stored tag.
 */
export function rememberSource(
  storage: Storage | undefined,
  workspaceSlug: string,
  pipelineSlug: string,
  source: SourceTag,
): void {
  if (!storage || source === "direct") return;
  try {
    storage.setItem(sourceKey(workspaceSlug, pipelineSlug), source);
  } catch {
    // Storage can be blocked (private mode); the tag in the URL still works.
  }
}

/** The tag to record on the application: the stored one, else "direct". */
export function applySource(
  storage: Storage | undefined,
  workspaceSlug: string,
  pipelineSlug: string,
): SourceTag {
  try {
    return parseSource(storage?.getItem(sourceKey(workspaceSlug, pipelineSlug)));
  } catch {
    return "direct";
  }
}

// The job description is plain text the TA team pasted. It is laid out as headings, paragraphs
// and lists, never rendered as HTML.

export type JdBlock =
  | { kind: "heading"; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "list"; items: string[] };

const BULLET = /^\s*(?:[-*•–·]|\d{1,2}[.)])\s+(.+)$/;
const HEADING_MAX = 60;

function isHeading(line: string, next: string | undefined, nextNonBlank: string | undefined) {
  const text = line.trim();
  if (text.endsWith(":")) return text.length <= HEADING_MAX + 20 && nextNonBlank !== undefined;
  if (text.length > HEADING_MAX || /[.!?,;]$/.test(text)) return false;
  // A short line directly above text, or above a list after a blank line.
  return (next !== undefined && next.trim() !== "") || BULLET.test(nextNonBlank ?? "");
}

export function parseJobDescription(text: string): JdBlock[] {
  const lines = text.replace(/\r\n?/g, "\n").split("\n");
  const blocks: JdBlock[] = [];
  // Whether the current paragraph or list may take the next line.
  let open = false;

  lines.forEach((line, index) => {
    if (!line.trim()) {
      // A blank line ends a paragraph; a list may carry on after it.
      const last = blocks.at(-1);
      open = last?.kind === "list";
      return;
    }
    const last = blocks.at(-1);
    const bullet = BULLET.exec(line);
    if (bullet) {
      const item = (bullet[1] ?? "").trim();
      if (open && last?.kind === "list") last.items.push(item);
      else blocks.push({ kind: "list", items: [item] });
      open = true;
      return;
    }
    const nextNonBlank = lines.slice(index + 1).find((item) => item.trim());
    if (isHeading(line, lines[index + 1], nextNonBlank)) {
      blocks.push({ kind: "heading", text: line.trim().replace(/:$/, "") });
      open = false;
      return;
    }
    if (open && last?.kind === "paragraph") last.text = `${last.text} ${line.trim()}`;
    else blocks.push({ kind: "paragraph", text: line.trim() });
    open = true;
  });
  return blocks;
}

/** The line above the title (FR-APPLY-01). */
export function statusLine(pipeline: PublicPipeline): string {
  const { availability, opens_at, closes_at, timezone } = pipeline;
  if (availability === "accepting") {
    return closes_at
      ? t("apply.status.acceptingUntil", { date: applyDate(closes_at, timezone) })
      : t("apply.status.accepting");
  }
  if (availability === "opens_later") {
    return opens_at
      ? t("apply.status.opensOn", { date: applyDate(opens_at, timezone) })
      : t("apply.status.opensLater");
  }
  return availability === "closed" ? t("apply.status.closed") : t("apply.status.notAccepting");
}

/** Why the Apply button is disabled, under it; null while the pipeline is accepting (FR-APPLY-06). */
export function unavailableReason(pipeline: PublicPipeline): string | null {
  const { availability, opens_at, timezone } = pipeline;
  if (availability === "accepting") return null;
  if (availability === "opens_later") {
    return opens_at
      ? t("apply.unavailable.opensOn", { date: applyDate(opens_at, timezone) })
      : t("apply.unavailable.opensLater");
  }
  return availability === "closed"
    ? t("apply.unavailable.closed")
    : t("apply.unavailable.notAccepting");
}

/** The "Your application is in" notice for where the application is (APPLY-004). */
export function appliedStatusText(
  status: CandidateStatus,
  values: { company: string; email: string },
): { title: string; body: string } {
  switch (status) {
    case "interview":
      return {
        title: t("apply.appliedStatus.interviewTitle"),
        body: t("apply.appliedStatus.interviewBody", values),
      };
    case "with_team":
      return {
        title: t("apply.appliedStatus.withTeamTitle", values),
        body: t("apply.appliedStatus.withTeamBody", values),
      };
    default:
      return {
        title: t("apply.appliedStatus.receivedTitle"),
        body: t("apply.appliedStatus.receivedBody"),
      };
  }
}
