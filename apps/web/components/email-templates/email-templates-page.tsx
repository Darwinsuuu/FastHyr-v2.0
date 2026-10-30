"use client";

import { ClockIcon, InfoIcon, PencilSimpleIcon, SparkleIcon } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { Badge, type BadgeTone } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { cn } from "@/lib/cn";
import {
  CATEGORY,
  type EmailTemplateSummary,
  FILTERS,
  filterCounts,
  matchesFilter,
  type TemplateCategory,
  type TemplateFilter,
} from "@/lib/email-templates";
import { formatDate, formatNumber } from "@/lib/format";
import { t } from "@/lib/i18n";

// The parameters every template can use, shown in the intro (the frame's list).
const INTRO_PARAMETERS = [
  "Candidate.firstname",
  "Candidate.lastname",
  "Job.title",
  "Company.name",
  "Interview.link",
  "Interview.expiry",
];

export const CATEGORY_TONE: Record<TemplateCategory, BadgeTone> = {
  invitation: "evergreen",
  reminder: "neutral",
  confirmation: "neutral",
  advancement: "evergreen",
  rejection: "persimmon",
  update: "neutral",
};

/** Email templates (frame EmailTemplates + A-07, FR-MSG-02): every candidate email as a card
 * with what it's for, when it goes and who changed it last. Admins and Recruiters. */
export function EmailTemplatesPage() {
  const { workspace } = useShell();
  const query = useQuery({
    queryKey: keys.emailTemplates(workspace.id),
    queryFn: async () => unwrap(await api.GET("/v1/email-templates")),
  });
  const [filter, setFilter] = useState<TemplateFilter>("all");
  const templates = query.data?.templates ?? [];
  const counts = filterCounts(templates.map((row) => row.key));
  const shown = templates.filter((row) => matchesFilter(row.key, filter));

  return (
    <div className="page-gutter flex flex-col gap-6 py-6 md:py-10 lg:px-10 lg:py-9">
      <header className="flex max-w-[680px] flex-col gap-2">
        <p className="type-label text-evergreen uppercase">{t("emailTemplates.eyebrow")}</p>
        <h1 className="type-heading">{t("emailTemplates.title")}</h1>
        <p className="type-body text-ink-muted">{t("emailTemplates.intro")}</p>
      </header>

      <div className="flex items-start gap-3 rounded-lg border border-line bg-surface-raised px-4 py-4 md:px-5">
        <InfoIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-evergreen" />
        <div className="flex min-w-0 flex-col gap-1">
          <p className="text-[14px] font-semibold">{t("emailTemplates.infoTitle")}</p>
          <p className="text-[13px] leading-5 text-ink-muted">
            {t("emailTemplates.infoBody")}{" "}
            {INTRO_PARAMETERS.map((name) => (
              <span key={name}>
                <code className="rounded-[4px] bg-surface-sunk px-1.5 py-px font-mono text-[12px] text-ink">
                  [{name}]
                </code>{" "}
              </span>
            ))}
          </p>
        </div>
      </div>

      <div
        role="group"
        aria-label={t("emailTemplates.filtersLabel")}
        className="-mx-4 flex gap-1.5 overflow-x-auto px-4 pb-1 md:mx-0 md:flex-wrap md:overflow-visible md:px-0 md:pb-0"
      >
        {FILTERS.map((option) => {
          const pressed = option === filter;
          return (
            <button
              key={option}
              type="button"
              aria-pressed={pressed}
              onClick={() => setFilter(option)}
              className={cn(
                "inline-flex h-11 shrink-0 items-center gap-2 rounded-pill border px-3 text-[13px] font-semibold whitespace-nowrap transition-colors md:h-9",
                pressed
                  ? "border-evergreen bg-evergreen text-on-evergreen"
                  : "border-line bg-surface-raised text-ink hover:border-line-strong",
              )}
            >
              {t(`emailTemplates.filters.${option}`)}
              <span
                className={cn(
                  "font-mono text-[12px] font-medium tabular-nums",
                  pressed ? "text-evergreen-soft" : "text-ink-muted",
                )}
              >
                {query.data ? formatNumber(counts[option]) : "…"}
              </span>
            </button>
          );
        })}
      </div>

      {query.isError ? (
        <div className="rounded-lg border border-line bg-surface-raised">
          <EmptyState title={t("emailTemplates.loadFailed")} />
        </div>
      ) : query.isPending ? (
        <div className="grid gap-4 md:grid-cols-2 md:gap-6 xl:grid-cols-3">
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} className="h-[260px] rounded-lg" />
          ))}
        </div>
      ) : shown.length === 0 ? (
        <div className="rounded-lg border border-line bg-surface-raised">
          <EmptyState title={t("emailTemplates.empty")} />
        </div>
      ) : (
        <ul className="grid gap-4 md:grid-cols-2 md:gap-6 xl:grid-cols-3">
          {shown.map((row) => (
            <li key={row.key} className="flex">
              <TemplateCard row={row} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function TemplateCard({ row }: { row: EmailTemplateSummary }) {
  const category = CATEGORY[row.key];
  const name = t(`emailTemplates.templates.${row.key}.name`);
  return (
    <article className="flex min-w-0 flex-1 flex-col gap-4 rounded-lg border border-line bg-surface-raised p-5 md:gap-[18px] md:p-6">
      <div>
        <Badge tone={CATEGORY_TONE[category]}>{t(`emailTemplates.category.${category}`)}</Badge>
      </div>
      <div className="flex min-w-0 flex-col gap-1.5">
        <h2 className="text-[17px] leading-6 font-[650]">{name}</h2>
        <p className="text-[14px] leading-5 text-ink-muted">
          {t(`emailTemplates.templates.${row.key}.description`)}
        </p>
        <p className="mt-2.5 truncate text-[13px] leading-[18px] text-ink-muted">
          <span className="font-semibold text-ink">{t("emailTemplates.subjectLabel")}</span>{" "}
          {row.subject}
        </p>
      </div>
      <p className="-mt-2 flex items-start gap-2 rounded-[8px] bg-surface-sunk px-3 py-2.5 text-[13px] leading-[18px]">
        <ClockIcon aria-hidden="true" className="mt-px size-4 shrink-0 text-ink-muted" />
        {t(`emailTemplates.templates.${row.key}.timing`)}
      </p>
      <div className="mt-auto flex items-center justify-between gap-3 border-t border-line pt-3.5">
        <EditedBy row={row} />
        <Link
          href={`/settings/email-templates/${row.key}`}
          aria-label={t("emailTemplates.editLabel", { name })}
          className="inline-flex h-11 shrink-0 items-center gap-1.5 rounded-[10px] border border-line-strong bg-surface-raised px-3.5 text-[13px] font-semibold text-ink transition-colors hover:bg-surface-sunk md:h-9"
        >
          <PencilSimpleIcon aria-hidden="true" className="size-4" />
          {t("emailTemplates.edit")}
        </Link>
      </div>
    </article>
  );
}

function EditedBy({ row }: { row: EmailTemplateSummary }) {
  if (row.is_default || !row.updated_by) {
    return (
      <span className="flex items-center gap-1.5 text-[12px] leading-4 text-ink-muted">
        <SparkleIcon aria-hidden="true" className="size-3.5 shrink-0" />
        {t("emailTemplates.usingDefault")}
      </span>
    );
  }
  return (
    <span className="min-w-0 text-[12px] leading-4 text-ink-muted">
      {t("emailTemplates.editedOn", { date: formatDate(row.updated_at, browserTimeZone()) })}
      <br />
      <span className="block truncate">
        {t("emailTemplates.editedBy", {
          name: row.updated_by.name || t("emailTemplates.editor.someone"),
        })}
      </span>
    </span>
  );
}

export function browserTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}
