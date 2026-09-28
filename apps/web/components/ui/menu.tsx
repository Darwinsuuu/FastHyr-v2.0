"use client";

import * as RadixDialog from "@radix-ui/react-dialog";
import * as RadixMenu from "@radix-ui/react-dropdown-menu";
import { type ReactElement, type ReactNode, useState } from "react";

import { cn } from "@/lib/cn";
import { useIsTabletUp } from "@/lib/hooks/use-media-query";

export type MenuEntry =
  | {
      label: string;
      onSelect: () => void;
      icon?: ReactNode;
      /** Red text; the action itself should still ask with a ConfirmDialog. */
      destructive?: boolean;
      disabled?: boolean;
    }
  | "separator";

export interface MenuProps {
  /** One focusable element, usually an IconButton ("More actions"). */
  trigger: ReactElement;
  items: MenuEntry[];
  /** Heading of the phone sheet, e.g. the row's name. */
  title: string;
  align?: "start" | "end";
}

const itemClasses = (destructive?: boolean) =>
  cn(
    "flex min-h-11 w-full cursor-pointer items-center gap-3 rounded-[8px] px-3 text-left text-[15px] outline-none select-none md:min-h-10 md:text-[14px]",
    "data-disabled:cursor-not-allowed data-disabled:opacity-45 disabled:cursor-not-allowed disabled:opacity-45",
    "data-highlighted:bg-surface-sunk hover:bg-surface-sunk",
    destructive ? "text-signal-gap" : "text-ink",
  );

/** Row actions: a dropdown from `md`, a bottom sheet on phones (RESPONSIVE.md §3). */
export function Menu({ trigger, items, title, align = "end" }: MenuProps) {
  const tabletUp = useIsTabletUp();
  const [open, setOpen] = useState(false);

  if (tabletUp) {
    return (
      <RadixMenu.Root modal={false}>
        <RadixMenu.Trigger asChild>{trigger}</RadixMenu.Trigger>
        <RadixMenu.Portal>
          <RadixMenu.Content
            align={align}
            sideOffset={6}
            collisionPadding={8}
            className="z-50 min-w-[220px] max-w-[280px] rounded-md border border-line bg-surface-raised p-1.5 shadow-raised data-[state=open]:animate-[fh-fade-in_160ms_ease-out]"
          >
            {items.map((item, index) =>
              item === "separator" ? (
                <RadixMenu.Separator key={index} className="my-1.5 h-px bg-line" />
              ) : (
                <RadixMenu.Item
                  key={item.label}
                  disabled={item.disabled}
                  onSelect={item.onSelect}
                  className={itemClasses(item.destructive)}
                >
                  {item.icon && (
                    <span className="flex size-5 items-center justify-center [&>svg]:size-5">
                      {item.icon}
                    </span>
                  )}
                  {item.label}
                </RadixMenu.Item>
              ),
            )}
          </RadixMenu.Content>
        </RadixMenu.Portal>
      </RadixMenu.Root>
    );
  }

  return (
    <RadixDialog.Root open={open} onOpenChange={setOpen}>
      <RadixDialog.Trigger asChild>{trigger}</RadixDialog.Trigger>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 z-40 bg-ink/45 data-[state=open]:animate-[fh-fade-in_200ms_ease-out]" />
        <RadixDialog.Content
          aria-describedby={undefined}
          className={cn(
            "fixed inset-x-0 bottom-0 z-50 rounded-t-lg bg-surface-raised px-3 pt-2",
            "pb-[max(12px,env(safe-area-inset-bottom))] data-[state=open]:animate-[fh-sheet-up_240ms_ease-out]",
          )}
        >
          <div aria-hidden="true" className="mx-auto mb-2 h-1 w-10 rounded-pill bg-line" />
          <RadixDialog.Title className="truncate px-3 pb-2 text-[13px] font-semibold text-ink-muted">
            {title}
          </RadixDialog.Title>
          <ul className="flex flex-col">
            {items.map((item, index) =>
              item === "separator" ? (
                <li key={index} role="separator" className="my-1.5 h-px bg-line" />
              ) : (
                <li key={item.label}>
                  <button
                    type="button"
                    disabled={item.disabled}
                    className={itemClasses(item.destructive)}
                    onClick={() => {
                      setOpen(false);
                      item.onSelect();
                    }}
                  >
                    {item.icon && (
                      <span className="flex size-5 items-center justify-center [&>svg]:size-5">
                        {item.icon}
                      </span>
                    )}
                    {item.label}
                  </button>
                </li>
              ),
            )}
          </ul>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
