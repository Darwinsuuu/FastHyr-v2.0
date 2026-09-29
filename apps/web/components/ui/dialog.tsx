"use client";

import { XIcon } from "@phosphor-icons/react";
import * as RadixDialog from "@radix-ui/react-dialog";
import { type ReactNode, type RefObject, useState } from "react";

import { Button, IconButton } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";

export interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  /** One or two sentences under the title; read by screen readers as the description. */
  description?: ReactNode;
  children?: ReactNode;
  /** Buttons; primary last. Sticky at the bottom on phones. */
  footer?: ReactNode;
  /** Width from `md`: sm 480, md 520, lg 640. */
  size?: "sm" | "md" | "lg";
  /** Blocks closing by Escape, scrim click and the close button (for work in progress). */
  dismissible?: boolean;
  /** Shown before the title, e.g. a 64 px avatar in the user profile. */
  leading?: ReactNode;
  /**
   * Where focus goes on close, for dialogs opened from a menu item (the item is gone by then).
   * Without it, focus returns to whatever was focused when the dialog opened.
   */
  returnFocusTo?: RefObject<HTMLElement | null>;
}

const WIDTHS = { sm: "md:max-w-[480px]", md: "md:max-w-[520px]", lg: "md:max-w-[640px]" };

/**
 * A modal dialog: a full-screen sheet with sticky footer buttons on phones, a centred
 * radius-lg dialog from `md` (RESPONSIVE.md §3). Focus is trapped and returns to the trigger.
 */
export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  size = "md",
  dismissible = true,
  leading,
  returnFocusTo,
}: DialogProps) {
  return (
    <RadixDialog.Root
      open={open}
      onOpenChange={(next) => (dismissible || next) && onOpenChange(next)}
    >
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 z-40 bg-ink/45 data-[state=open]:animate-[fh-fade-in_200ms_ease-out]" />
        <RadixDialog.Content
          onEscapeKeyDown={(event) => !dismissible && event.preventDefault()}
          onOpenAutoFocus={(event) => {
            // Focus the first field rather than the close button, whose tooltip would open on focus.
            event.preventDefault();
            const content = event.currentTarget as HTMLElement;
            const first = content.querySelector<HTMLElement>(
              "[data-dialog-body] :is(input, select, textarea, button)",
            );
            (first ?? content).focus();
          }}
          onCloseAutoFocus={(event) => {
            if (!returnFocusTo?.current) return;
            event.preventDefault();
            returnFocusTo.current.focus();
          }}
          onPointerDownOutside={(event) => !dismissible && event.preventDefault()}
          {...(description ? {} : { "aria-describedby": undefined })}
          className={cn(
            "fixed inset-0 z-50 flex flex-col bg-surface-raised text-ink outline-none",
            "md:inset-auto md:top-1/2 md:left-1/2 md:max-h-[calc(100dvh-64px)] md:w-[calc(100vw-64px)] md:-translate-x-1/2 md:-translate-y-1/2",
            "md:rounded-lg md:shadow-raised",
            "data-[state=open]:animate-[fh-rise_240ms_ease-out]",
            WIDTHS[size],
          )}
        >
          <div className="flex items-start gap-3 px-4 pt-[max(16px,env(safe-area-inset-top))] md:px-7 md:pt-7">
            {leading}
            <div className={cn("min-w-0 flex-1", leading ? "self-center" : "pt-1.5")}>
              <RadixDialog.Title className="text-[22px] leading-7 font-[650] tracking-[-0.01em]">
                {title}
              </RadixDialog.Title>
              {description && (
                <RadixDialog.Description className="mt-2 text-[15px] leading-6 text-ink-muted">
                  {description}
                </RadixDialog.Description>
              )}
            </div>
            {dismissible && (
              <RadixDialog.Close asChild>
                <IconButton
                  label={t("ui.close")}
                  size="sm"
                  icon={<XIcon className="size-5" />}
                  className="-mr-1 max-md:size-11"
                />
              </RadixDialog.Close>
            )}
          </div>
          {children && (
            <div data-dialog-body className="flex-1 overflow-y-auto px-4 pt-5 pb-2 md:px-7">
              {children}
            </div>
          )}
          {!children && <div className="flex-1 md:hidden" />}
          {footer && (
            <div
              className={cn(
                "flex flex-col-reverse gap-2 border-t border-line px-4 pt-3 pb-[max(16px,env(safe-area-inset-bottom))]",
                "md:flex-row md:justify-end md:border-0 md:px-7 md:pt-5 md:pb-7",
                "max-md:[&>*]:w-full",
              )}
            >
              {footer}
            </div>
          )}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}

export interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  /** Say exactly what happens and what doesn't, e.g. "Candidates who applied keep their results." */
  description: ReactNode;
  confirmLabel: string;
  /** Defaults to "Cancel". */
  cancelLabel?: string;
  destructive?: boolean;
  /** Awaited; the dialog stays open with a loading button until it settles, and closes on success. */
  onConfirm: () => void | Promise<void>;
  children?: ReactNode;
  side?: "ta" | "candidate";
}

/** Asks before an action. The confirm button names the action ("Close pipeline"), never "OK". */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  cancelLabel,
  destructive,
  onConfirm,
  children,
  side = "ta",
  confirmDisabled,
}: ConfirmDialogProps & { confirmDisabled?: boolean }) {
  const [busy, setBusy] = useState(false);

  async function confirm() {
    setBusy(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      description={description}
      size="sm"
      dismissible={!busy}
      footer={
        <>
          <Button
            variant="secondary"
            side={side}
            disabled={busy}
            onClick={() => onOpenChange(false)}
          >
            {cancelLabel ?? t("ui.cancel")}
          </Button>
          <Button
            side={side}
            destructive={destructive}
            loading={busy}
            disabled={confirmDisabled}
            onClick={() => void confirm()}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      {children}
    </Dialog>
  );
}

export interface TypeToConfirmDialogProps extends Omit<ConfirmDialogProps, "children"> {
  /** The exact phrase to type, e.g. "I understand" or the workspace name. */
  phrase: string;
}

/** For actions no one can undo: the confirm button enables only when the exact phrase is typed. */
export function TypeToConfirmDialog({
  phrase,
  open,
  onOpenChange,
  ...props
}: TypeToConfirmDialogProps) {
  const [typed, setTyped] = useState("");
  return (
    <ConfirmDialog
      {...props}
      open={open}
      onOpenChange={(next) => {
        if (!next) setTyped("");
        onOpenChange(next);
      }}
      destructive={props.destructive ?? true}
      confirmDisabled={typed !== phrase}
    >
      <Field label={t("ui.typeToConfirm", { phrase })}>
        <Input
          value={typed}
          autoComplete="off"
          spellCheck={false}
          onChange={(event) => setTyped(event.target.value)}
        />
      </Field>
    </ConfirmDialog>
  );
}
