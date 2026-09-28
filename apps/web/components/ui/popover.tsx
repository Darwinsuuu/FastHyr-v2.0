"use client";

import * as RadixPopover from "@radix-ui/react-popover";
import type { ReactElement, ReactNode } from "react";

import { cn } from "@/lib/cn";

export interface PopoverProps {
  trigger: ReactElement;
  children: ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  align?: "start" | "center" | "end";
  className?: string;
}

/** Non-modal panel anchored to its trigger (filters, "How we got to 91" details). Fits the screen on phones. */
export function Popover({
  trigger,
  children,
  open,
  onOpenChange,
  align = "start",
  className,
}: PopoverProps) {
  return (
    <RadixPopover.Root open={open} onOpenChange={onOpenChange}>
      <RadixPopover.Trigger asChild>{trigger}</RadixPopover.Trigger>
      <RadixPopover.Portal>
        <RadixPopover.Content
          align={align}
          sideOffset={6}
          collisionPadding={8}
          className={cn(
            "z-50 w-[min(320px,calc(100vw-16px))] rounded-md border border-line bg-surface-raised p-4 text-ink shadow-raised",
            "data-[state=open]:animate-[fh-fade-in_160ms_ease-out]",
            className,
          )}
        >
          {children}
        </RadixPopover.Content>
      </RadixPopover.Portal>
    </RadixPopover.Root>
  );
}
