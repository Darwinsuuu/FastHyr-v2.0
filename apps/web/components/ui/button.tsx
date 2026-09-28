"use client";

import { type ButtonHTMLAttributes, forwardRef, type ReactNode } from "react";

import { Spinner } from "@/components/ui/spinner";
import { Tooltip } from "@/components/ui/tooltip";
import { cn } from "@/lib/cn";

export type ButtonVariant = "primary" | "secondary" | "quiet";
export type Side = "ta" | "candidate";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** primary (filled), secondary (outlined), quiet (text). One primary per screen. */
  variant?: ButtonVariant;
  /** "ta" = evergreen (hiring screens), "candidate" = persimmon (candidate screens). */
  side?: Side;
  size?: ButtonSize;
  /** Destructive actions: a red outline/text for secondary and quiet, a red fill for primary. */
  destructive?: boolean;
  /** Shows a spinner, keeps the width and blocks clicks. */
  loading?: boolean;
  /** A 20 px Phosphor icon before the label. */
  icon?: ReactNode;
}

// Sizes from the frames: sm 36 px, md 44 px (touch target), lg 48 px.
const SIZES: Record<ButtonSize, string> = {
  sm: "min-h-9 px-3.5 text-[13px] leading-[18px] rounded-[10px] gap-1.5",
  md: "min-h-11 px-5 text-[15px] leading-5 rounded-md gap-2",
  lg: "min-h-12 px-6 text-[15px] leading-5 rounded-md gap-2",
};

function variantClasses(variant: ButtonVariant, side: Side, destructive: boolean): string {
  if (destructive) {
    return {
      primary: "bg-signal-gap text-surface-raised hover:brightness-95",
      secondary: "border border-signal-gap bg-surface-raised text-signal-gap hover:bg-surface-sunk",
      quiet: "text-signal-gap hover:bg-surface-sunk",
    }[variant];
  }
  if (variant === "primary") {
    return side === "ta"
      ? "bg-evergreen text-on-evergreen hover:brightness-110"
      : "bg-persimmon text-on-persimmon hover:brightness-105";
  }
  if (variant === "secondary") {
    return "border border-line-strong bg-surface-raised text-ink hover:border-ink";
  }
  return side === "ta"
    ? "text-evergreen hover:bg-evergreen-soft"
    : "text-persimmon-ink hover:bg-persimmon-soft";
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "primary",
    side = "ta",
    size = "md",
    destructive = false,
    loading = false,
    icon,
    className,
    children,
    disabled,
    type = "button",
    ...props
  },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center font-semibold whitespace-nowrap",
        "transition-[background-color,border-color,filter] duration-200 ease-out",
        "disabled:cursor-not-allowed disabled:opacity-45",
        SIZES[size],
        variantClasses(variant, side, destructive),
        className,
      )}
      {...props}
    >
      {loading && (
        <span className="absolute inset-0 flex items-center justify-center">
          <Spinner />
        </span>
      )}
      <span className={cn("inline-flex items-center gap-[inherit]", loading && "invisible")}>
        {icon}
        {children}
      </span>
    </button>
  );
});

export interface IconButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> {
  /** Required: read by screen readers and shown as the tooltip. */
  label: string;
  icon: ReactNode;
  size?: "sm" | "md";
}

/** Icon-only button with an aria-label and a tooltip; 44 px touch target at md. */
export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, icon, size = "md", className, type = "button", ...props },
  ref,
) {
  return (
    <Tooltip content={label}>
      <button
        ref={ref}
        type={type}
        aria-label={label}
        className={cn(
          "inline-flex shrink-0 items-center justify-center rounded-[10px] text-ink-muted",
          "transition-colors duration-200 ease-out hover:bg-surface-sunk hover:text-ink",
          "disabled:cursor-not-allowed disabled:opacity-45",
          size === "md" ? "size-11" : "size-9",
          className,
        )}
        {...props}
      >
        {icon}
      </button>
    </Tooltip>
  );
});
