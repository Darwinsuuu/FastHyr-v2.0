"use client";

import { CheckCircleIcon, WarningCircleIcon, XIcon } from "@phosphor-icons/react";
import * as RadixToast from "@radix-ui/react-toast";
import { createContext, type ReactNode, useCallback, useContext, useMemo, useState } from "react";

import { t } from "@/lib/i18n";
import { cn } from "@/lib/cn";

export interface ToastOptions {
  title: string;
  description?: string;
  /** "error" is announced assertively and stays until dismissed. */
  tone?: "success" | "info" | "error";
  /** One quick action, e.g. Undo. */
  action?: { label: string; onClick: () => void };
}

interface ToastItem extends ToastOptions {
  id: number;
}

const ToastContext = createContext<((options: ToastOptions) => void) | null>(null);

/** Shows a toast: `const toast = useToast(); toast({ title: "Pipeline paused" })`. */
export function useToast() {
  const show = useContext(ToastContext);
  if (!show) throw new Error("useToast needs <ToastProvider> above it");
  return show;
}

/** Holds the toast queue. Bottom centre on phones (above the safe area), bottom right from md. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const show = useCallback((options: ToastOptions) => {
    setItems((current) => [...current.slice(-2), { ...options, id: Date.now() + Math.random() }]);
  }, []);
  const remove = useCallback(
    (id: number) => setItems((current) => current.filter((item) => item.id !== id)),
    [],
  );
  const value = useMemo(() => show, [show]);

  return (
    <ToastContext.Provider value={value}>
      <RadixToast.Provider swipeDirection="down" duration={5000} label={t("ui.dismiss")}>
        {children}
        {items.map((item) => (
          <RadixToast.Root
            key={item.id}
            type={item.tone === "error" ? "foreground" : "background"}
            duration={item.tone === "error" ? Number.POSITIVE_INFINITY : undefined}
            onOpenChange={(open) => !open && remove(item.id)}
            className={cn(
              "flex items-start gap-3 rounded-md bg-ink p-4 text-surface-raised shadow-raised",
              "data-[state=open]:animate-[fh-rise_240ms_ease-out] data-[swipe=move]:translate-y-[var(--radix-toast-swipe-move-y)]",
            )}
          >
            {item.tone === "error" ? (
              <WarningCircleIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
            ) : (
              <CheckCircleIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
            )}
            <div className="min-w-0 flex-1">
              <RadixToast.Title className="text-[15px] leading-5 font-semibold">
                {item.title}
              </RadixToast.Title>
              {item.description && (
                <RadixToast.Description className="mt-1 text-[14px] leading-5 opacity-85">
                  {item.description}
                </RadixToast.Description>
              )}
            </div>
            {item.action && (
              <RadixToast.Action
                altText={item.action.label}
                onClick={item.action.onClick}
                className="-my-1.5 min-h-9 rounded-[8px] px-2 text-[14px] font-semibold underline underline-offset-4"
              >
                {item.action.label}
              </RadixToast.Action>
            )}
            <RadixToast.Close
              aria-label={t("ui.dismiss")}
              className="-my-2 -mr-2 flex size-9 shrink-0 items-center justify-center rounded-[8px] opacity-80 hover:opacity-100"
            >
              <XIcon aria-hidden="true" className="size-4" />
            </RadixToast.Close>
          </RadixToast.Root>
        ))}
        <RadixToast.Viewport
          className={cn(
            "fixed inset-x-0 bottom-0 z-[60] flex flex-col gap-2 px-4 pb-[max(16px,env(safe-area-inset-bottom))] outline-none",
            "md:inset-x-auto md:right-0 md:w-[400px] md:px-6 md:pb-6",
          )}
        />
      </RadixToast.Provider>
    </ToastContext.Provider>
  );
}
