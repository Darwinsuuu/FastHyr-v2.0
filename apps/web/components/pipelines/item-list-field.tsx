"use client";

import { EyeSlashIcon } from "@phosphor-icons/react";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { ChipInput } from "@/components/ui/chip-input";
import { Field } from "@/components/ui/field";
import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";
import { MAX_ITEMS, MIN_ITEMS } from "@/lib/pipelines/wizard";

/**
 * Must-haves and skills to probe: a chip list hidden from candidates, at least 3 to continue.
 * The count turns red once someone tried to continue without enough (`tried`).
 */
export function ItemListField({
  label,
  hint,
  placeholder,
  value,
  onValueChange,
  tried,
  error,
  children,
}: {
  label: string;
  hint: string;
  placeholder: string;
  value: string[];
  onValueChange: (value: string[]) => void;
  tried: boolean;
  /** Shown once a blocked Continue was tried. */
  error?: string;
  /** Extra content under the field, e.g. the fairness note. */
  children?: ReactNode;
}) {
  const enough = value.length >= MIN_ITEMS;
  return (
    <div className="flex flex-col gap-3">
      <Field
        label={
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span>{label}</span>
            <Badge tone="outline" icon={<EyeSlashIcon aria-hidden="true" />}>
              {t("pipelines.wizard.hiddenFromCandidates")}
            </Badge>
            <span
              className={cn(
                "ml-auto text-[13px] font-semibold",
                enough ? "text-evergreen" : tried ? "text-signal-gap" : "text-signal-watch",
              )}
            >
              {enough
                ? t("pipelines.wizard.countAdded", { count: value.length })
                : t("pipelines.wizard.countMin", { count: value.length })}
            </span>
          </span>
        }
        hint={hint}
        error={tried && !enough ? error : undefined}
      >
        <ChipInput
          value={value}
          onValueChange={onValueChange}
          placeholder={placeholder}
          max={MAX_ITEMS}
        />
      </Field>
      {children}
    </div>
  );
}
