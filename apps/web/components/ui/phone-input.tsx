"use client";

import { useFieldControl } from "@/components/ui/field";
import { controlClasses } from "@/components/ui/input";
import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";

/** Dialling codes offered first; the list is short on purpose (launch markets), then the rest alphabetically. */
export const DIAL_CODES: { country: string; code: string; name: string }[] = [
  { country: "PH", code: "+63", name: "Philippines" },
  { country: "SG", code: "+65", name: "Singapore" },
  { country: "MY", code: "+60", name: "Malaysia" },
  { country: "ID", code: "+62", name: "Indonesia" },
  { country: "AU", code: "+61", name: "Australia" },
  { country: "IN", code: "+91", name: "India" },
  { country: "GB", code: "+44", name: "United Kingdom" },
  { country: "US", code: "+1", name: "United States" },
];

export interface PhoneValue {
  country: string;
  number: string;
}

export interface PhoneInputProps {
  value: PhoneValue;
  onValueChange: (value: PhoneValue) => void;
  disabled?: boolean;
  className?: string;
}

/** Country code + number. The number keeps only digits and spaces; the code is a native select (best on phones). */
export function PhoneInput({ value, onValueChange, disabled, className }: PhoneInputProps) {
  const field = useFieldControl();
  const current = DIAL_CODES.find((item) => item.country === value.country);
  return (
    <div className={cn("flex gap-2", className)}>
      <select
        aria-label={t("ui.countryCode")}
        disabled={disabled}
        value={value.country}
        onChange={(event) => onValueChange({ ...value, country: event.target.value })}
        className={cn(controlClasses, "h-12 w-[104px] shrink-0 px-3")}
      >
        {DIAL_CODES.map((item) => (
          <option key={item.country} value={item.country}>
            {item.country} {item.code}
          </option>
        ))}
      </select>
      <input
        {...field}
        type="tel"
        inputMode="tel"
        autoComplete="tel-national"
        disabled={disabled}
        placeholder={current?.country === "PH" ? "917 123 4567" : undefined}
        value={value.number}
        onChange={(event) =>
          onValueChange({ ...value, number: event.target.value.replace(/[^\d ]/g, "") })
        }
        className={cn(controlClasses, "h-12 min-w-0 flex-1 px-3.5")}
      />
    </div>
  );
}
