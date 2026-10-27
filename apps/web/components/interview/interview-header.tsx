import type { ReactNode } from "react";

import { CompanyMark } from "@/components/apply/company-mark";
import { TurnMark } from "@/components/brand/turn-mark";
import { t } from "@/lib/i18n";
import type { InterviewCompany } from "@/lib/interview";

/**
 * "{Company} · interviews with FastHyr" (frames DemoDeviceCheck and DemoInterview), with the
 * live interview's time remaining and status on the right (`children`). The review request page
 * (S-03) passes its own `tagline`.
 */
export function InterviewHeader({
  company,
  tagline = t("interview.interviewsWith"),
  children,
}: {
  company: InterviewCompany;
  tagline?: string;
  children?: ReactNode;
}) {
  return (
    <header className="border-b border-line">
      <div className="page-gutter flex min-h-16 items-center justify-between gap-3 py-3 md:min-h-[72px]">
        <div className="flex min-w-0 items-center gap-3">
          <CompanyMark company={company} size="sm" />
          <p className="min-w-0 text-[14px] leading-5 text-ink-muted md:text-[15px]">
            <span className="font-semibold break-words text-ink">{company.name}</span>
            <span className={children ? "max-lg:hidden" : undefined}>
              {" · "}
              {tagline}{" "}
              <span className="inline-flex items-center gap-1 align-bottom">
                <TurnMark size={14} />
                <span className="font-display font-semibold text-ink">{t("site.name")}</span>
              </span>
            </span>
          </p>
        </div>
        {children && <div className="flex shrink-0 items-center gap-4 md:gap-5">{children}</div>}
      </div>
    </header>
  );
}
