import Link from "next/link";
import type { ReactNode } from "react";

import { TurnMark } from "@/components/brand/turn-mark";
import { t } from "@/lib/i18n";

// The EmployerLogin frame's split layout, shared by the sign-in, reset-password and verify-email
// screens. Phones get a slim evergreen band with the logo above the content; from lg the band
// becomes the full-height panel with the headline, as in the frame.
export function AuthSplitLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col bg-surface lg:flex-row">
      <section className="relative flex shrink-0 flex-col justify-between overflow-hidden bg-evergreen text-on-evergreen lg:min-h-dvh lg:w-[44%] lg:max-w-[640px] lg:px-16 lg:py-14 xl:px-18">
        <Link
          href="/"
          aria-label={t("auth.homeLink")}
          className="flex min-h-14 items-center gap-2.5 self-start px-4 py-3 md:px-6 lg:min-h-0 lg:p-0"
        >
          <TurnMark size={32} reversed />
          <span className="font-display text-[22px] font-semibold tracking-[-0.02em]">
            {t("site.name")}
          </span>
        </Link>
        <svg
          viewBox="0 0 420 420"
          aria-hidden="true"
          className="pointer-events-none absolute top-[180px] -right-[120px] hidden size-[420px] opacity-[0.14] lg:block"
        >
          <ellipse cx="160" cy="190" rx="160" ry="190" className="fill-on-evergreen" />
          <ellipse cx="300" cy="270" rx="120" ry="150" className="fill-on-evergreen" />
        </svg>
        <div className="relative hidden flex-col gap-5 lg:flex">
          <p className="text-[12px] font-semibold tracking-[0.08em] uppercase opacity-80">
            {t("auth.panelEyebrow")}
          </p>
          <p className="type-display-lg">{t("auth.panelHeadline")}</p>
          <p className="max-w-[440px] text-[17px] leading-[1.6] opacity-90">
            {t("auth.panelBody")}
          </p>
        </div>
        <p className="relative hidden text-[13px] opacity-70 lg:block">
          {t("auth.copyright", { year: new Date().getFullYear() })}
        </p>
      </section>
      <main className="page-gutter flex flex-1 justify-center py-8 sm:py-12 lg:items-center lg:py-12">
        <div className="w-full max-w-[420px]">{children}</div>
      </main>
    </div>
  );
}
