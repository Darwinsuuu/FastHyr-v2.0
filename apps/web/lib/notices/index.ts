// Versioned candidate notices and consent texts (COMP-002, PRIVACY.md §3). The words come from
// the API (`/v1/public/notices`), never from messages/en.json: every record stores the notice id
// the candidate agreed to, so the text shown must be exactly that version's.

import { type components, createApiClient, unwrap } from "@fasthyr/api-client";

import { env } from "@/lib/env";

export type Notice = components["schemas"]["Notice"];
export type CurrentNotices = components["schemas"]["CurrentNotices"];
export type NoticeKind = Notice["kind"];
export type NoticeLink = Notice["links"][number];

/** What fills a notice's placeholders: the company name, and an option per `choices` key
 * (e.g. `{ interview: pipeline.interview_format }`). */
export interface NoticeValues {
  company: string;
  choices?: Record<string, string | null | undefined>;
}

export interface FilledNotice {
  /** Stored on the record when the candidate agrees, e.g. `apply@v1`. */
  id: string;
  statement: string;
  details: string[];
  links: NoticeLink[];
}

const PLACEHOLDER = /\{([^{}]*)\}/g;

/** Fills `{company}` and each choice placeholder. A missing value throws rather than showing a
 * consent with a gap in it. */
export function fillNotice(notice: Notice, values: NoticeValues): FilledNotice {
  const fill = (text: string) =>
    text.replace(PLACEHOLDER, (_, name: string) => {
      if (name === "company") return values.company;
      const option = values.choices?.[name];
      const wording = option ? notice.choices[name]?.[option] : undefined;
      if (wording === undefined) {
        throw new Error(`${notice.id}: no wording for {${name}}`);
      }
      return wording;
    });
  return {
    id: notice.id,
    statement: fill(notice.statement),
    details: notice.details.map(fill),
    links: notice.links,
  };
}

/** Where each notice link goes. The pages live on the public site (WEB-005). */
export const NOTICE_LINK_PATHS: Record<NoticeLink, string> = {
  privacy: "/privacy",
  ai_in_hiring: "/ai-in-hiring",
  terms: "/terms",
};

export function noticeLinkHref(link: NoticeLink): string {
  return `${env.siteUrl}${NOTICE_LINK_PATHS[link]}`;
}

// No sign-in needed, so a plain client works on the server and in the browser.
const publicApi = createApiClient({ baseUrl: env.apiUrl });

/** The current version of every notice. Server pages call it directly; client code uses
 * `useNotices()`. */
export async function loadNotices(): Promise<CurrentNotices> {
  return unwrap(await publicApi.GET("/v1/public/notices", { cache: "no-store" }));
}

/** One released version, e.g. to show what a record agreed to. */
export async function loadNoticeVersion(kind: NoticeKind, version: number): Promise<Notice> {
  return unwrap(
    await publicApi.GET("/v1/public/notices/{kind}/{version}", {
      params: { path: { kind, version } },
    }),
  );
}
