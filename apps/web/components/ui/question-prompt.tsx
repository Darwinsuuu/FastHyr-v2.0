import type { ReactNode } from "react";

import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";

export interface QuestionPromptProps {
  step: number;
  total: number;
  question: string;
  /** Why we're asking, tied to their own résumé (persimmon-soft). */
  context?: string;
  /** Reassurance, not coaching. */
  hint?: string;
  /** Actions: usually one primary Button side="candidate" and one quiet one. */
  children?: ReactNode;
  className?: string;
}

/** The candidate's interview stage: one question, where it came from, and what to do next. */
export function QuestionPrompt({
  step,
  total,
  question,
  context,
  hint,
  children,
  className,
}: QuestionPromptProps) {
  const label = t("prompt.questionOf", { step, total });
  return (
    <section
      aria-label={label}
      className={cn(
        "flex w-full max-w-[720px] flex-col gap-4 rounded-lg bg-surface-raised p-6 shadow-raised sm:p-8 md:p-12",
        "animate-[fh-rise_320ms_ease-out]",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-4">
        <span className="type-label text-ink-muted">{label}</span>
        <span aria-hidden="true" className="inline-flex gap-1.5">
          {Array.from({ length: total }, (_, index) => {
            const number = index + 1;
            return (
              <i
                key={number}
                className={cn(
                  "block h-2 rounded-pill",
                  number === step ? "w-6 bg-persimmon" : "w-2",
                  number < step ? "bg-persimmon-ink" : number > step && "bg-line",
                )}
              />
            );
          })}
        </span>
      </div>
      <h2 className="font-display text-[28px] leading-[34px] font-[560] tracking-[-0.015em] text-ink md:text-[40px] md:leading-[46px]">
        {question}
      </h2>
      {context && (
        <p className="rounded-sm bg-persimmon-soft px-4 py-3 text-body text-ink">{context}</p>
      )}
      {hint && <p className="text-body-sm text-ink-muted">{hint}</p>}
      {children && (
        <div className="mt-4 flex flex-col gap-2 sm:flex-row [&>*]:max-sm:w-full">{children}</div>
      )}
    </section>
  );
}
