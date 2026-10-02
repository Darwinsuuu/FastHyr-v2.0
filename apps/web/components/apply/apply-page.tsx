import {
  ArrowUpRightIcon,
  BriefcaseIcon,
  FlagIcon,
  GlobeIcon,
  HeartIcon,
  HouseLineIcon,
  MapPinIcon,
  ShieldCheckIcon,
  SquaresFourIcon,
  UsersIcon,
} from "@phosphor-icons/react/dist/ssr";
import type { Icon } from "@phosphor-icons/react";
import type { ReactNode } from "react";

import { AppliedNotice, ApplyButton, ApplyHint } from "@/components/apply/apply-button";
import { ApplySessionProvider } from "@/components/apply/apply-session";
import { CandidateMenu } from "@/components/apply/candidate-menu";
import { CompanyMark } from "@/components/apply/company-mark";
import { TurnMark } from "@/components/brand/turn-mark";
import {
  applyDate,
  parseJobDescription,
  type PublicPipeline,
  type SourceTag,
  statusLine,
  unavailableReason,
} from "@/lib/apply";
import type { Candidate, ReturnState } from "@/lib/apply/session";
import { cn } from "@/lib/cn";
import { type MessageKey, t } from "@/lib/i18n";
import type { Notice } from "@/lib/notices";

/**
 * The public apply page (frame Apply, FR-APPLY-01): the employer's brand, the role and its status,
 * how applying works and the company. Mobile first: one column, then the role facts beside the
 * content from `lg`.
 */
export function ApplyPage({
  pipeline,
  source,
  candidate,
  appliedAt,
  notice,
  returning,
}: {
  pipeline: PublicPipeline;
  source: SourceTag;
  /** The signed-in candidate (Google or Microsoft), if any (APPLY-002). */
  candidate: Candidate | null;
  /** When that candidate applied to this pipeline, if they have (APPLY-003). */
  appliedAt: string | null;
  /** The current apply notice for the form's consent (COMP-002). */
  notice: Notice | null;
  /** Back from the sign-in round trip (APPLY-002). */
  returning: ReturnState;
}) {
  const { company } = pipeline;
  const unavailable = unavailableReason(pipeline);
  const buttonProps = {
    workspaceSlug: pipeline.workspace_slug,
    pipelineSlug: pipeline.slug,
    source,
    timeZone: pipeline.timezone,
    unavailable,
  };

  return (
    <ApplySessionProvider
      pipeline={pipeline}
      source={source}
      initialCandidate={candidate}
      initialAppliedAt={appliedAt}
      notice={notice}
      returning={returning}
    >
      <div className="flex min-h-dvh flex-col bg-surface">
        <header className="sticky top-0 z-20 border-b border-line bg-surface/95 backdrop-blur-sm">
          <div className="page-gutter flex h-16 items-center justify-between gap-4 md:h-[72px]">
            <div className="flex min-w-0 items-center gap-3">
              <CompanyMark company={company} size="sm" />
              <span className="flex min-w-0 flex-col">
                <span className="truncate text-[15px] leading-5 font-bold">{company.name}</span>
                <span className="text-[12px] leading-4 text-ink-muted">{t("apply.careers")}</span>
              </span>
            </div>
            <div className="flex shrink-0 items-center gap-4.5">
              {/* The footer names FastHyr too, so phones keep the header for the account. */}
              <span className="hidden items-center gap-1.5 text-[12px] text-ink-muted sm:flex">
                <TurnMark size={16} />
                {t("apply.hiringWith")}
                <strong className="font-display font-semibold text-ink">{t("site.name")}</strong>
              </span>
              <CandidateMenu />
            </div>
          </div>
        </header>

        <main className="flex-1">
          <section className="border-b border-line bg-surface-raised">
            <div className="page-gutter flex flex-col gap-6 py-8 md:py-12 lg:flex-row lg:items-end lg:justify-between lg:gap-12">
              <div className="flex min-w-0 flex-col gap-3.5">
                <p className="flex items-center gap-2 text-[13px] leading-5 text-ink-muted">
                  <span
                    aria-hidden="true"
                    className={cn(
                      "size-2 shrink-0 rounded-pill",
                      pipeline.availability === "accepting"
                        ? "bg-evergreen"
                        : pipeline.availability === "opens_later"
                          ? "bg-marigold"
                          : "bg-ink-muted",
                    )}
                  />
                  {statusLine(pipeline)}
                </p>
                <h1 className="type-display-lg break-words lg:type-display-xl">{pipeline.title}</h1>
                <MetaChips pipeline={pipeline} />
              </div>
              <div className="flex shrink-0 flex-col gap-2.5 lg:items-end">
                <ApplyButton {...buttonProps} showArrow remember className="w-full sm:w-auto" />
                <ApplyHint unavailable={unavailable} />
              </div>
            </div>
          </section>

          <div className="page-gutter grid gap-10 pt-10 pb-16 md:pt-12 lg:grid-cols-[minmax(0,1fr)_400px] lg:items-start lg:gap-12 lg:pb-[72px]">
            <div className="flex min-w-0 flex-col gap-9">
              <AppliedNotice />
              <section aria-labelledby="about-role" className="flex flex-col gap-3.5">
                <h2 id="about-role" className="font-display text-[28px] leading-[34px] font-[560]">
                  {t("apply.aboutRole")}
                </h2>
                <JobDescription text={pipeline.jd_text} />
              </section>
              <OpenTo pipeline={pipeline} />
              <HowItWorks pipeline={pipeline} />
            </div>

            <aside className="flex flex-col gap-4.5 lg:sticky lg:top-24">
              <Card>
                <h2 className="type-label text-ink-muted">{t("apply.facts.title")}</h2>
                <Facts pipeline={pipeline} />
                <ApplyButton {...buttonProps} size="md" className="w-full" />
              </Card>
              <CompanyCard company={company} />
            </aside>
          </div>
        </main>

        <footer className="border-t border-line">
          <p className="page-gutter py-6 text-[13px] leading-5 text-ink-muted">
            {t("apply.footer", { company: company.name })}
          </p>
        </footer>
      </div>
    </ApplySessionProvider>
  );
}

function Card({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col gap-4 rounded-[20px] border border-line bg-surface-raised p-5 md:p-6">
      {children}
    </div>
  );
}

function label(prefix: string, value: string | null | undefined): string | null {
  return value ? t(`${prefix}.${value}` as MessageKey) : null;
}

function MetaChips({ pipeline }: { pipeline: PublicPipeline }) {
  const chips: [Icon, string | null][] = [
    [SquaresFourIcon, pipeline.department],
    [BriefcaseIcon, label("pipelines.wizard.role.employmentTypes", pipeline.employment_type)],
    [HouseLineIcon, label("pipelines.wizard.role.workSetups", pipeline.work_setup)],
    [MapPinIcon, pipeline.location],
  ];
  return (
    <ul className="flex flex-wrap items-center gap-2">
      {chips
        .filter((chip): chip is [Icon, string] => Boolean(chip[1]))
        .map(([ChipIcon, text]) => (
          <li
            key={text}
            className="flex min-h-8 items-center gap-2 rounded-pill border border-line bg-surface px-3 py-1 text-[14px] leading-5"
          >
            <ChipIcon aria-hidden="true" className="size-[15px] shrink-0 text-evergreen" />
            {text}
          </li>
        ))}
    </ul>
  );
}

function JobDescription({ text }: { text: string }) {
  return (
    <div className="flex flex-col gap-3.5 text-ink">
      {parseJobDescription(text).map((block, index) => {
        if (block.kind === "heading") {
          return (
            <h3
              key={index}
              className={cn("text-[19px] leading-[26px] font-bold", index > 0 && "mt-4")}
            >
              {block.text}
            </h3>
          );
        }
        if (block.kind === "list") {
          return (
            <ul key={index} className="flex flex-col gap-2.5">
              {block.items.map((item, itemIndex) => (
                <li
                  key={itemIndex}
                  className="grid grid-cols-[20px_minmax(0,1fr)] gap-2.5 text-[16px] leading-[26px] text-ink/85"
                >
                  <span
                    aria-hidden="true"
                    className="mt-2.5 ml-1.5 size-1.5 rounded-pill bg-persimmon"
                  />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          );
        }
        return (
          <p key={index} className="text-[16px] leading-[27px] break-words text-ink/85">
            {block.text}
          </p>
        );
      })}
    </div>
  );
}

function OpenTo({ pipeline }: { pipeline: PublicPipeline }) {
  if (pipeline.open_to.length === 0) return null;
  return (
    <section className="flex gap-4 rounded-[16px] border border-persimmon-soft bg-persimmon-soft/45 p-5 md:px-[22px]">
      <span
        aria-hidden="true"
        className="hidden size-9 shrink-0 items-center justify-center rounded-[10px] bg-persimmon-soft text-persimmon sm:flex"
      >
        <HeartIcon className="size-[18px]" />
      </span>
      <div className="flex flex-col gap-2.5">
        <h2 className="text-[16px] leading-[22px] font-bold">{t("apply.openToTitle")}</h2>
        <ul className="flex flex-col gap-2.5">
          {pipeline.open_to.map((option) => (
            <li key={option} className="text-[15px] leading-[23px] text-ink/85">
              <strong className="text-persimmon-ink">
                {t(`pipelines.wizard.role.openToOptions.${option}.label`)}.
              </strong>{" "}
              {t(`pipelines.wizard.role.openToOptions.${option}.description`)}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function HowItWorks({ pipeline }: { pipeline: PublicPipeline }) {
  const steps: [string, MessageKey, MessageKey][] = [
    ["01", "apply.howItWorks.step1Title", "apply.howItWorks.step1Body"],
    ["02", "apply.howItWorks.step2Title", "apply.howItWorks.step2Body"],
    [
      "03",
      "apply.howItWorks.step3Title",
      pipeline.interview_format === "voice_only"
        ? "apply.howItWorks.step3BodyVoice"
        : "apply.howItWorks.step3BodyVideo",
    ],
  ];
  return (
    <section aria-labelledby="how-it-works" className="flex flex-col gap-4">
      <h2 id="how-it-works" className="type-title font-bold">
        {t("apply.howItWorks.title")}
      </h2>
      <ol className="grid gap-3.5 md:grid-cols-3">
        {steps.map(([number, title, body]) => (
          <li
            key={number}
            className="flex flex-col gap-2.5 rounded-[16px] border border-line bg-surface-raised p-[18px]"
          >
            <span
              aria-hidden="true"
              className="flex size-8 items-center justify-center rounded-pill bg-evergreen font-mono text-[12px] font-semibold text-on-evergreen"
            >
              {number}
            </span>
            <strong className="text-[15px] leading-[21px]">{t(title)}</strong>
            <span className="text-[14px] leading-[22px] text-ink-muted">{t(body)}</span>
          </li>
        ))}
      </ol>
      <p className="flex items-start gap-2.5 text-[14px] leading-[22px] text-ink-muted">
        <ShieldCheckIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-evergreen" />
        {t("apply.fairness", { company: pipeline.company.name })}
      </p>
    </section>
  );
}

function Facts({ pipeline }: { pipeline: PublicPipeline }) {
  const { timezone } = pipeline;
  const facts: [MessageKey, string | null][] = [
    ["apply.facts.department", pipeline.department],
    [
      "apply.facts.employmentType",
      label("pipelines.wizard.role.employmentTypes", pipeline.employment_type),
    ],
    ["apply.facts.workSetup", label("pipelines.wizard.role.workSetups", pipeline.work_setup)],
    ["apply.facts.location", pipeline.location],
    [
      "apply.facts.interview",
      pipeline.interview_format === "voice_only"
        ? t("apply.facts.interviewVoice")
        : t("apply.facts.interviewVideo"),
    ],
    pipeline.availability === "opens_later"
      ? ["apply.facts.opens", pipeline.opens_at ? applyDate(pipeline.opens_at, timezone) : null]
      : ["apply.facts.closes", pipeline.closes_at ? applyDate(pipeline.closes_at, timezone) : null],
  ];
  return (
    <dl className="flex flex-col gap-3.5">
      {facts
        .filter((fact): fact is [MessageKey, string] => Boolean(fact[1]))
        .map(([key, value]) => (
          <div key={key} className="flex justify-between gap-4 text-[14px] leading-5">
            <dt className="text-ink-muted">{t(key)}</dt>
            <dd className="text-right font-semibold">{value}</dd>
          </div>
        ))}
    </dl>
  );
}

function regionName(code: string): string {
  return new Intl.DisplayNames(["en"], { type: "region" }).of(code) ?? code;
}

function CompanyCard({ company }: { company: PublicPipeline["company"] }) {
  const details: [Icon, MessageKey, string | null][] = [
    [
      FlagIcon,
      "apply.company.industry",
      label("companyProfile.industry.options", company.industry),
    ],
    [
      UsersIcon,
      "apply.company.size",
      company.company_size
        ? t("apply.company.sizeValue", {
            size: t(`companyProfile.size.options.${company.company_size}`),
          })
        : null,
    ],
    [
      GlobeIcon,
      "apply.company.headquarters",
      company.hq_country ? regionName(company.hq_country) : null,
    ],
  ];
  const links: [MessageKey, string | null][] = [
    ["apply.company.website", company.website],
    ["apply.company.otherRoles", company.careers_url],
  ];
  const shown = details.filter((detail): detail is [Icon, MessageKey, string] =>
    Boolean(detail[2]),
  );
  const shownLinks = links.filter((link): link is [MessageKey, string] => Boolean(link[1]));

  return (
    <Card>
      <div className="flex items-center gap-3">
        <CompanyMark company={company} size="lg" />
        <span className="flex min-w-0 flex-col gap-0.5">
          <h2 className="type-label text-ink-muted">{t("apply.company.title")}</h2>
          <span className="truncate font-display text-[22px] leading-7 font-[560]">
            {company.name}
          </span>
        </span>
      </div>
      {company.about && (
        <p className="text-[14px] leading-[23px] break-words whitespace-pre-line text-ink/85">
          {company.about}
        </p>
      )}
      {shown.length > 0 && (
        <dl className="flex flex-col gap-2.5 border-t border-line pt-3.5">
          {shown.map(([DetailIcon, key, value]) => (
            <div key={key} className="flex items-center gap-2.5 text-[14px] leading-5">
              <DetailIcon aria-hidden="true" className="size-4 shrink-0 text-ink-muted" />
              <dt className="w-28 shrink-0 text-ink-muted">{t(key)}</dt>
              <dd className="font-semibold">{value}</dd>
            </div>
          ))}
        </dl>
      )}
      {shownLinks.length > 0 && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-[14px] font-semibold">
          {shownLinks.map(([key, href]) => (
            <a
              key={key}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex min-h-11 items-center gap-1 text-persimmon-ink underline-offset-4 hover:underline"
            >
              {t(key)}
              <ArrowUpRightIcon aria-hidden="true" className="size-3.5" />
              <span className="sr-only">{t("apply.company.newTab")}</span>
            </a>
          ))}
        </div>
      )}
    </Card>
  );
}
