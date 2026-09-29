"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";

import { ForgotPasswordDialog } from "@/components/auth/forgot-password-dialog";
import { PasswordInput } from "@/components/auth/password-input";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { continuePath } from "@/lib/auth/flow";
import { MIN_PASSWORD_LENGTH } from "@/lib/auth/password";
import { type NewPasswordOutcome, saveNewPassword } from "@/lib/auth/recovery";
import { env } from "@/lib/env";
import { type MessageKey, t } from "@/lib/i18n";
import { supabaseBrowser } from "@/lib/supabase/browser";

type Problem = { field: "password" | "confirm"; key: MessageKey };

const SAVE_PROBLEMS: Partial<Record<NewPasswordOutcome, MessageKey>> = {
  "same-password": "auth.reset.samePassword",
  "weak-password": "auth.error.weakPassword",
  "rate-limited": "auth.error.rateLimited",
  failed: "auth.reset.failed",
};

function checkPasswords(password: string, confirm: string): Problem | null {
  if (password.length < MIN_PASSWORD_LENGTH) {
    return { field: "password", key: "auth.error.tooShort" };
  }
  if (password !== confirm) {
    return { field: "confirm", key: "auth.reset.mismatch" };
  }
  return null;
}

export function ResetPasswordForm({ linkValid }: { linkValid: boolean }) {
  const [problem, setProblem] = useState<Problem | null>(null);
  const [busy, setBusy] = useState(false);
  const [expired, setExpired] = useState(!linkValid);
  const [dialogOpen, setDialogOpen] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password"));
    const found = checkPasswords(password, String(form.get("confirm")));
    setProblem(found);
    if (found) return;

    setBusy(true);
    const outcome = await saveNewPassword(supabaseBrowser().auth, password);
    if (outcome === "saved") {
      window.location.assign(new URL(continuePath(null), env.siteUrl).toString());
      return;
    }
    setBusy(false);
    if (outcome === "expired") {
      setExpired(true);
      return;
    }
    setProblem({ field: "password", key: SAVE_PROBLEMS[outcome] ?? "auth.reset.failed" });
  }

  if (expired) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="type-heading lg:text-[30px] lg:leading-9">{t("auth.reset.expiredTitle")}</h1>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button size="lg" onClick={() => setDialogOpen(true)}>
            {t("auth.reset.sendNewLink")}
          </Button>
          <Link
            href="/login"
            className="inline-flex min-h-12 items-center justify-center rounded-md px-6 text-[15px] font-semibold text-evergreen hover:bg-evergreen-soft"
          >
            {t("auth.forgot.backToSignIn")}
          </Link>
        </div>
        <ForgotPasswordDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          onBackToSignIn={() => window.location.assign(new URL("/login", env.siteUrl).toString())}
        />
      </div>
    );
  }

  const errorFor = (field: Problem["field"]) => (problem?.field === field ? t(problem.key) : null);

  return (
    <div className="flex flex-col gap-7">
      <h1 className="type-heading lg:text-[30px] lg:leading-9">{t("auth.reset.title")}</h1>
      <form noValidate className="flex flex-col gap-[18px]" onSubmit={submit}>
        <Field label={t("auth.reset.newPassword")} error={errorFor("password")} required>
          <PasswordInput
            name="password"
            autoComplete="new-password"
            placeholder={t("auth.passwordPlaceholder")}
          />
        </Field>
        <Field label={t("auth.reset.confirmPassword")} error={errorFor("confirm")} required>
          <PasswordInput name="confirm" autoComplete="new-password" />
        </Field>
        <Button type="submit" size="lg" className="mt-1.5 w-full" loading={busy}>
          {t("auth.reset.save")}
        </Button>
      </form>
    </div>
  );
}
