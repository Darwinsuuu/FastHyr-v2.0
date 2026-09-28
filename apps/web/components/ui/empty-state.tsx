import type { ReactNode } from "react";

import { TurnMark } from "@/components/brand/turn-mark";
import { cn } from "@/lib/cn";

export interface EmptyStateProps {
  title: string;
  /** What this place will hold and how to fill it. */
  description?: ReactNode;
  /** Usually one Button. */
  action?: ReactNode;
  className?: string;
}

/** Nothing here yet: the Turn, a plain title, one line of help and at most one action. */
export function EmptyState({ title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center px-4 py-12 text-center", className)}>
      <TurnMark size={48} />
      <h2 className="mt-5 type-title text-ink">{title}</h2>
      {description && (
        <p className="mt-2 max-w-[42ch] text-[15px] leading-6 text-ink-muted">{description}</p>
      )}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
