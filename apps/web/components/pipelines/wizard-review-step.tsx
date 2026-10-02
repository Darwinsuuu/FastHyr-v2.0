"use client";

import { LockIcon } from "@phosphor-icons/react";

import type { StepProps } from "@/components/pipelines/wizard-role-step";
import { formatDayLong, formatNumber } from "@/lib/format";
import { t } from "@/lib/i18n";
import {
  closeDate,
  type DepartmentOption,
  missingDetails,
  NO_DEPARTMENT,
  type StepId,
  startOfDay,
} from "@/lib/pipelines/wizard";

interface Row {
  term: string;
  value: string;
  /** A required detail that is still empty. */
  missing?: boolean;
}

export interface ReviewStepProps extends Omit<StepProps, "update" | "tried"> {
  departments: DepartmentOption[];
  freeCredits: number | null;
  /** A scheduled pipeline being edited, with the credits it holds. */
  scheduled?: { reserved: number };
  onEdit: (step: StepId) => void;
}

/** Step 5, Review (frame NewPipeline step 5, FR-PIPE-05): what will lock, and every choice. */
export function ReviewStep({ form, departments, freeCredits, scheduled, onEdit }: ReviewStepProps) {
  const missing = missingDetails(form);
  const later = form.open_mode === "scheduled";
  const opens = later && form.opens_on ? formatDayLong(startOfDay(form.opens_on)) : null;
  const notSet = t("pipelines.wizard.review.notSet");
  const list = (items: string[], empty: string) => items.join(" · ") || empty;
  const department =
    departments.find((option) => option.value === (form.department_id ?? NO_DEPARTMENT))?.label ??
    t("departments.noDepartment");
  const messages = [
    form.email_resume_reject ? t("pipelines.wizard.review.messageReject") : null,
    form.email_post_interview ? t("pipelines.wizard.review.messageResult") : null,
  ].filter((value): value is string => value !== null);

  const sections: { step: StepId; rows: Row[] }[] = [
    {
      step: "role",
      rows: [
        {
          term: t("pipelines.wizard.review.rows.title"),
          value: form.title.trim() || notSet,
          missing: missing.has("title"),
        },
        { term: t("pipelines.wizard.review.rows.department"), value: department },
        {
          term: t("pipelines.wizard.review.rows.workSetup"),
          value: `${t(`pipelines.wizard.role.workSetups.${form.work_setup}`)} · ${t(`pipelines.wizard.role.employmentTypes.${form.employment_type}`)}`,
        },
        ...(form.work_setup === "remote" && !form.location.trim()
          ? []
          : [
              {
                term: t("pipelines.wizard.review.rows.location"),
                value: form.location.trim() || notSet,
                missing: missing.has("location"),
              },
            ]),
        {
          term: t("pipelines.wizard.review.rows.jd"),
          value: form.jd_text.trim()
            ? t("pipelines.wizard.review.jdAdded", {
                count: formatNumber(form.jd_text.trim().length),
              })
            : notSet,
          missing: missing.has("jd_text"),
        },
        {
          term: t("pipelines.wizard.review.rows.mustHaves"),
          value: list(form.must_haves, t("pipelines.wizard.review.noneYet")),
        },
        {
          term: t("pipelines.wizard.review.rows.openTo"),
          value: list(
            form.open_to.map((id) => t(`pipelines.wizard.role.openToOptions.${id}.label`)),
            t("pipelines.wizard.review.none"),
          ),
        },
      ],
    },
    {
      step: "interview",
      rows: [
        {
          term: t("pipelines.wizard.review.rows.format"),
          value: t(`pipelines.wizard.interview.formats.${form.interview_format}.label`),
        },
        {
          term: t("pipelines.wizard.review.rows.toneDepth"),
          value: `${t(`pipelines.wizard.interview.tones.${form.tone}.label`)} · ${t(`pipelines.wizard.interview.seniorities.${form.seniority}`)}`,
        },
        {
          term: t("pipelines.wizard.review.rows.skills"),
          value: list(form.skills_to_probe, t("pipelines.wizard.review.noneYet")),
        },
        {
          term: t("pipelines.wizard.review.rows.integrity"),
          value: form.integrity_enabled
            ? t("pipelines.wizard.review.integrityOn")
            : t("pipelines.wizard.review.off"),
        },
      ],
    },
    {
      step: "scoring",
      rows: [
        {
          term: t("pipelines.wizard.review.rows.rubric"),
          value: t("pipelines.wizard.review.rubricValue", {
            technical: form.weight_technical,
            communication: form.weight_communication,
            culture: form.weight_culture,
          }),
        },
        {
          term: t("pipelines.wizard.review.rows.passMark"),
          value: t("pipelines.wizard.scoring.passMarkValue", { value: form.pass_mark }),
        },
        {
          term: t("pipelines.wizard.review.rows.messages"),
          value: list(messages, t("pipelines.wizard.review.none")),
        },
      ],
    },
    {
      step: "schedule",
      rows: [
        {
          term: t("pipelines.wizard.review.rows.opens"),
          value: later ? (opens ?? notSet) : t("pipelines.wizard.review.opensNow"),
          missing: later && !opens,
        },
        {
          term: t("pipelines.wizard.review.rows.closes"),
          value: t("pipelines.wizard.review.closesValue", {
            date: formatDayLong(closeDate(form)),
            days: form.duration_days,
          }),
        },
        {
          term: t("pipelines.wizard.review.rows.credits"),
          value: scheduled
            ? t("pipelines.wizard.review.creditsReserved", {
                credits: formatNumber(scheduled.reserved),
              })
            : freeCredits === null
              ? formatNumber(form.credits_to_reserve)
              : t("pipelines.wizard.review.creditsValue", {
                  credits: formatNumber(form.credits_to_reserve),
                  free: formatNumber(freeCredits),
                }),
          missing: !scheduled && freeCredits !== null && form.credits_to_reserve > freeCredits,
        },
      ],
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-3.5 rounded-md bg-persimmon-soft p-4">
        <span
          aria-hidden="true"
          className="flex size-9 shrink-0 items-center justify-center rounded-sm bg-surface-raised text-persimmon-ink"
        >
          <LockIcon className="size-[18px]" />
        </span>
        <div className="flex flex-col gap-0.5 text-ink">
          <p className="text-[15px] leading-5 font-[650]">
            {later
              ? t("pipelines.wizard.review.lockLaterTitle", { date: opens ?? notSet })
              : t("pipelines.wizard.review.lockNowTitle")}
          </p>
          <p className="text-[14px] leading-5">
            {later
              ? t("pipelines.wizard.review.lockLaterBody")
              : t("pipelines.wizard.review.lockNowBody")}
          </p>
        </div>
      </div>

      {sections.map(({ step, rows }) => {
        const title = t(`pipelines.wizard.steps.${step}.label`);
        return (
          <section
            key={step}
            aria-labelledby={`review-${step}`}
            className="flex flex-col gap-3 rounded-md border border-line p-4 md:p-5"
          >
            <div className="flex items-center justify-between gap-3">
              <h3 id={`review-${step}`} className="text-[16px] leading-6 font-[650] text-ink">
                {title}
              </h3>
              <button
                type="button"
                onClick={() => onEdit(step)}
                aria-label={t("pipelines.wizard.review.editSection", { section: title })}
                className="-mr-2 inline-flex min-h-11 items-center rounded-sm px-2 text-[14px] font-semibold text-evergreen hover:bg-evergreen-soft"
              >
                {t("pipelines.wizard.review.edit")}
              </button>
            </div>
            <dl className="grid gap-y-3 text-[14px] leading-5 sm:grid-cols-[180px_minmax(0,1fr)] sm:gap-x-4 sm:gap-y-2">
              {rows.map((row) => (
                <div key={row.term} className="flex flex-col gap-0.5 sm:contents">
                  <dt className="text-ink-muted">{row.term}</dt>
                  <dd
                    className={
                      row.missing
                        ? "font-semibold break-words text-signal-gap"
                        : "break-words text-ink"
                    }
                  >
                    {row.value}
                  </dd>
                </div>
              ))}
            </dl>
          </section>
        );
      })}
    </div>
  );
}
