"use client";

import { CaretRightIcon } from "@phosphor-icons/react";
import { Fragment } from "react";

import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";
import { fillNotice, type Notice, type NoticeValues, noticeLinkHref } from "@/lib/notices";

const LINK_LABELS = {
  privacy: "consent.link.privacy",
  ai_in_hiring: "consent.link.aiInHiring",
  terms: "consent.link.terms",
} as const;

/**
 * A versioned consent (COMP-002): the notice's statement as the checkbox label with its links,
 * and "What this means" with the details. `card` is the apply form's bordered box (frame Apply);
 * `plain` is the device check's line (frame DemoDeviceCheck, S-01). Send `notice.id` with the
 * form so the record keeps the version the candidate agreed to.
 */
export function ConsentCheckbox({
  notice,
  values,
  checked,
  onCheckedChange,
  error,
  variant = "card",
  className,
}: {
  notice: Notice;
  values: NoticeValues;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  /** e.g. "Please agree before sending your application." */
  error?: string;
  variant?: "card" | "plain";
  className?: string;
}) {
  const filled = fillNotice(notice, values);
  return (
    <div
      data-notice={filled.id}
      className={cn(
        "flex flex-col",
        variant === "card" &&
          "rounded-[12px] border bg-surface px-3.5 pb-3 transition-colors md:px-4",
        variant === "card" && (error ? "border-signal-gap" : "border-line"),
        className,
      )}
    >
      <Checkbox
        required
        checked={checked}
        onCheckedChange={onCheckedChange}
        error={error}
        className={variant === "card" ? "pt-3" : undefined}
        label={
          <>
            {filled.statement}
            {filled.links.map((link, index) => (
              <Fragment key={link}>
                {index === 0 ? " " : " · "}
                <a
                  href={noticeLinkHref(link)}
                  target="_blank"
                  rel="noopener"
                  className="font-semibold text-evergreen underline hover:text-persimmon"
                >
                  {t(LINK_LABELS[link])}
                  <span className="sr-only"> {t("consent.newTab")}</span>
                </a>
              </Fragment>
            ))}
          </>
        }
      />
      {filled.details.length > 0 && (
        <details className="group pl-8">
          <summary className="flex min-h-11 w-fit cursor-pointer list-none items-center gap-1 text-[13px] font-semibold text-evergreen hover:text-persimmon md:min-h-8 [&::-webkit-details-marker]:hidden">
            <CaretRightIcon
              aria-hidden="true"
              weight="bold"
              className="size-3.5 transition-transform group-open:rotate-90 motion-reduce:transition-none"
            />
            {t("consent.details")}
          </summary>
          <ul className="flex list-disc flex-col gap-1.5 pt-1 pb-1 pl-4 text-[13px] leading-5 text-ink-muted">
            {filled.details.map((detail) => (
              <li key={detail}>{detail}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
