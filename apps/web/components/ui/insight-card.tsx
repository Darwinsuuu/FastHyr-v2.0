import type { ReactNode } from "react";

import { type SignalLevel, Signal } from "@/components/ui/signal";
import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";

export interface InsightCardProps {
  /** Eyebrow, e.g. "Leadership". Defaults to "From the résumé". */
  topic?: string;
  level?: SignalLevel;
  /** Verbatim résumé text; always include it when there is one so the claim can be traced. */
  excerpt?: string;
  /** The one exact phrase inside `excerpt` the question came from (marigold). */
  highlight?: string;
  /** The finding, in evidence language. No verdicts. */
  finding: string;
  /** The interview question it became. */
  question?: string;
  children?: ReactNode;
  className?: string;
}

/** Splits `text` around the first occurrence of `phrase` so it can be marked. */
export function splitHighlight(text: string, phrase?: string): [string, string, string] | null {
  if (!phrase) return null;
  const index = text.indexOf(phrase);
  if (index < 0) return null;
  return [text.slice(0, index), phrase, text.slice(index + phrase.length)];
}

/** The small Turn used before a generated question: the asking half larger and higher. */
function TurnGlyph() {
  return (
    <span aria-hidden="true" className="inline-flex shrink-0 gap-0.5 pt-0.5">
      <i className="block h-4 w-2 rounded-l-full bg-evergreen" />
      <i className="mt-1.5 block h-3 w-1.5 rounded-r-full bg-persimmon" />
    </span>
  );
}

/** The hiring side's signature card: a résumé finding, its evidence, and the question it became. */
export function InsightCard({
  topic,
  level,
  excerpt,
  highlight,
  finding,
  question,
  children,
  className,
}: InsightCardProps) {
  const parts = excerpt ? splitHighlight(excerpt, highlight) : null;
  return (
    <article
      className={cn(
        "flex w-full max-w-[560px] flex-col gap-4 rounded-md border border-line bg-surface-raised p-4 md:p-6",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="type-label text-ink-muted">{topic ?? t("insight.fromResume")}</span>
        {level && <Signal level={level} />}
      </div>
      {excerpt && (
        <blockquote className="rounded-sm bg-surface-sunk px-4 py-3 font-mono text-[13px] leading-5 text-ink">
          {parts ? (
            <>
              {parts[0]}
              <mark className="rounded-[2px] bg-marigold px-0.5 text-on-marigold">{parts[1]}</mark>
              {parts[2]}
            </>
          ) : (
            excerpt
          )}
        </blockquote>
      )}
      <p className="text-[15px] leading-[22px] text-ink">{finding}</p>
      {question && (
        <div className="flex gap-3 border-t border-line pt-4">
          <TurnGlyph />
          <div>
            <span className="type-label text-ink-muted">{t("insight.becomesQuestion")}</span>
            <p className="mt-1 font-display text-[20px] leading-7 font-[450] text-ink italic">
              {question}
            </p>
          </div>
        </div>
      )}
      {children}
    </article>
  );
}
