"use client";

import { CheckIcon } from "@phosphor-icons/react";
import * as RadixDialog from "@radix-ui/react-dialog";
import * as RadixMenu from "@radix-ui/react-dropdown-menu";
import { type ReactElement, type ReactNode, useState } from "react";

import { cn } from "@/lib/cn";
import { useIsTabletUp } from "@/lib/hooks/use-media-query";

export type ShellMenuEntry =
  | {
      /** Stable key; for a `radio` entry, the value it selects. */
      id: string;
      label: string;
      description?: string;
      /** A 28 px tile or avatar in front of the label. */
      leading?: ReactNode;
      /** Part of the menu's single-choice group (the workspaces); `radioValue` marks the chosen one. */
      radio?: boolean;
      destructive?: boolean;
      onSelect: () => void;
    }
  | "separator";

export interface ShellMenuProps {
  trigger: ReactElement;
  /** The menu's accessible name, and the heading of the phone sheet. */
  title: string;
  /** Small caption above the items (e.g. "Your workspaces"). */
  caption?: string;
  /** A block above the items (e.g. the user's name and role). */
  header?: ReactNode;
  entries: ShellMenuEntry[];
  radioValue?: string;
  side?: "bottom" | "right";
  align?: "start" | "end";
  open: boolean;
  onOpenChange: (open: boolean) => void;
  className?: string;
}

const itemClasses = (destructive?: boolean) =>
  cn(
    "flex min-h-11 w-full cursor-pointer items-center gap-2.5 rounded-[8px] px-2 py-2 text-left outline-none select-none md:min-h-10",
    "data-highlighted:bg-surface-sunk hover:bg-surface-sunk data-[state=checked]:bg-surface-sunk aria-[current=true]:bg-surface-sunk",
    destructive ? "text-signal-gap" : "text-ink",
  );

function EntryBody({
  entry,
  checked,
}: {
  entry: Exclude<ShellMenuEntry, "separator">;
  checked: boolean;
}) {
  return (
    <>
      {entry.leading}
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="truncate text-[15px] leading-5 font-semibold md:text-[14px] md:leading-[18px]">
          {entry.label}
        </span>
        {entry.description && (
          <span className="truncate text-[13px] leading-4 text-ink-muted md:text-[12px]">
            {entry.description}
          </span>
        )}
      </span>
      {checked && (
        <CheckIcon aria-hidden="true" weight="bold" className="size-4 shrink-0 text-evergreen" />
      )}
    </>
  );
}

/** The shell's menus: a popover from `md`, a bottom sheet on phones (RESPONSIVE.md §3). */
export function ShellMenu({
  trigger,
  title,
  caption,
  header,
  entries,
  radioValue,
  side = "bottom",
  align = "start",
  open,
  onOpenChange,
  className,
}: ShellMenuProps) {
  const tabletUp = useIsTabletUp();
  const captionNode = caption && (
    <div className="px-2 pt-2 pb-1.5 text-[11px] font-[650] tracking-[0.06em] text-ink-muted uppercase">
      {caption}
    </div>
  );

  if (tabletUp) {
    // Radio entries sit together in one group, as in the frame's workspace list.
    const radios = entries.filter((entry) => entry !== "separator" && entry.radio);
    const rest = entries.filter((entry) => entry === "separator" || !entry.radio);
    return (
      <RadixMenu.Root modal={false} open={open} onOpenChange={onOpenChange}>
        <RadixMenu.Trigger asChild>{trigger}</RadixMenu.Trigger>
        <RadixMenu.Portal>
          <RadixMenu.Content
            aria-label={title}
            // Named by `title`, not by the trigger's label.
            aria-labelledby={undefined}
            side={side}
            align={align}
            sideOffset={8}
            collisionPadding={8}
            className={cn(
              "z-50 flex w-[280px] flex-col gap-0.5 rounded-md border border-line bg-surface-raised p-1.5 text-ink shadow-raised",
              "data-[state=open]:animate-[fh-fade-in_160ms_ease-out]",
              className,
            )}
          >
            {header}
            {captionNode}
            {radios.length > 0 && (
              <RadixMenu.RadioGroup value={radioValue}>
                {radios.map(
                  (entry) =>
                    entry !== "separator" && (
                      <RadixMenu.RadioItem
                        key={entry.id}
                        value={entry.id}
                        onSelect={entry.onSelect}
                        className={itemClasses(entry.destructive)}
                      >
                        <EntryBody entry={entry} checked={entry.id === radioValue} />
                      </RadixMenu.RadioItem>
                    ),
                )}
              </RadixMenu.RadioGroup>
            )}
            {rest.map((entry, index) =>
              entry === "separator" ? (
                <RadixMenu.Separator key={`sep-${index}`} className="my-1.5 h-px bg-line" />
              ) : (
                <RadixMenu.Item
                  key={entry.id}
                  onSelect={entry.onSelect}
                  className={itemClasses(entry.destructive)}
                >
                  <EntryBody entry={entry} checked={false} />
                </RadixMenu.Item>
              ),
            )}
          </RadixMenu.Content>
        </RadixMenu.Portal>
      </RadixMenu.Root>
    );
  }

  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Trigger asChild>{trigger}</RadixDialog.Trigger>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 z-[60] bg-ink/45 data-[state=open]:animate-[fh-fade-in_200ms_ease-out]" />
        <RadixDialog.Content
          aria-describedby={undefined}
          className={cn(
            "fixed inset-x-0 bottom-0 z-[60] max-h-[85dvh] overflow-y-auto rounded-t-lg bg-surface-raised px-3 pt-2 text-ink",
            "pb-[max(12px,env(safe-area-inset-bottom))] data-[state=open]:animate-[fh-sheet-up_240ms_ease-out]",
          )}
        >
          <div aria-hidden="true" className="mx-auto mb-2 h-1 w-10 rounded-pill bg-line" />
          <RadixDialog.Title
            className={
              header || caption
                ? "sr-only"
                : "truncate px-2 pb-2 text-[13px] font-semibold text-ink-muted"
            }
          >
            {title}
          </RadixDialog.Title>
          {header}
          {captionNode}
          <ul className="flex flex-col gap-0.5">
            {entries.map((entry, index) =>
              entry === "separator" ? (
                <li key={`sep-${index}`} role="separator" className="my-1.5 h-px bg-line" />
              ) : (
                <li key={entry.id}>
                  <button
                    type="button"
                    aria-current={entry.radio && entry.id === radioValue ? "true" : undefined}
                    className={itemClasses(entry.destructive)}
                    onClick={() => {
                      onOpenChange(false);
                      entry.onSelect();
                    }}
                  >
                    <EntryBody entry={entry} checked={!!entry.radio && entry.id === radioValue} />
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

/** Controlled open state for a ShellMenu. */
export function useMenuState() {
  const [open, setOpen] = useState(false);
  return { open, onOpenChange: setOpen };
}
