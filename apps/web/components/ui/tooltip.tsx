"use client";

import * as RadixTooltip from "@radix-ui/react-tooltip";
import { type ReactElement, type ReactNode, useRef, useState } from "react";

import { cn } from "@/lib/cn";

/** Wrap the app once so tooltips share their open delay. */
export function TooltipProvider({ children }: { children: ReactNode }) {
  return <RadixTooltip.Provider delayDuration={300}>{children}</RadixTooltip.Provider>;
}

/**
 * A short label for its trigger. Opens on hover and focus, and on tap too (RESPONSIVE.md §2:
 * hover-only information must also open on tap). The trigger must be one focusable element.
 */
export function Tooltip({
  content,
  side = "top",
  children,
}: {
  content: ReactNode;
  side?: "top" | "right" | "bottom" | "left";
  children: ReactElement;
}) {
  const [open, setOpen] = useState(false);
  // Radix closes a tooltip on pointer down and click; on touch we reopen it after the tap settles.
  const tapOpens = useRef(false);
  return (
    <RadixTooltip.Provider delayDuration={300}>
      <RadixTooltip.Root open={open} onOpenChange={setOpen}>
        <RadixTooltip.Trigger
          asChild
          onPointerDown={(event) => {
            tapOpens.current = event.pointerType === "touch" && !open;
          }}
          onClick={() => {
            if (!tapOpens.current) return;
            tapOpens.current = false;
            setTimeout(() => setOpen(true), 0);
          }}
        >
          {children}
        </RadixTooltip.Trigger>
        <RadixTooltip.Portal>
          <RadixTooltip.Content
            side={side}
            sideOffset={8}
            collisionPadding={8}
            className={cn(
              "z-50 max-w-64 rounded-[8px] bg-ink px-3 py-1.5 text-[13px] leading-[18px] font-semibold text-surface-raised",
            )}
          >
            {content}
          </RadixTooltip.Content>
        </RadixTooltip.Portal>
      </RadixTooltip.Root>
    </RadixTooltip.Provider>
  );
}
