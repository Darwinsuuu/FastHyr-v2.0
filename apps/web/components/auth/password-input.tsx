"use client";

import { EyeIcon, EyeSlashIcon } from "@phosphor-icons/react";
import { forwardRef, type InputHTMLAttributes, useState } from "react";

import { IconButton } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { t } from "@/lib/i18n";

/** Password field with a show/hide toggle (S-05). Use inside a `Field`. */
export const PasswordInput = forwardRef<
  HTMLInputElement,
  Omit<InputHTMLAttributes<HTMLInputElement>, "type">
>(function PasswordInput(props, ref) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative">
      <Input ref={ref} type={visible ? "text" : "password"} className="pr-12" {...props} />
      <IconButton
        label={t(visible ? "auth.reset.hidePassword" : "auth.reset.showPassword")}
        size="sm"
        icon={
          visible ? (
            <EyeSlashIcon aria-hidden="true" className="size-5" />
          ) : (
            <EyeIcon aria-hidden="true" className="size-5" />
          )
        }
        className="absolute top-1/2 right-1.5 -translate-y-1/2"
        onClick={() => setVisible((shown) => !shown)}
      />
    </div>
  );
});
