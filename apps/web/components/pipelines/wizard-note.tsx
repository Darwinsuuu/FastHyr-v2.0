import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/** The wizard's evergreen side notes (fairness, Also open to, adaptive interview). */
export function WizardNote({
  icon,
  children,
  className,
}: {
  icon: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex gap-3 rounded-md bg-evergreen-soft/50 p-3.5 text-[14px] leading-[21px] text-ink",
        "[&>svg]:mt-0.5 [&>svg]:size-[18px] [&>svg]:shrink-0 [&>svg]:text-evergreen",
        className,
      )}
    >
      {icon}
      <p>{children}</p>
    </div>
  );
}
