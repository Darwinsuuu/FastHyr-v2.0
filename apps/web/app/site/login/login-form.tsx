"use client";

import { EnvelopeSimpleIcon, WarningCircleIcon } from "@phosphor-icons/react";
import Link from "next/link";
import { type FormEvent, useState } from "react";

import { GoogleMark, MicrosoftMark } from "@/components/auth/provider-marks";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { continuePath, type OAuthProvider, OAUTH_SCOPES } from "@/lib/auth/flow";
import { continueWithPassword, type PasswordOutcome } from "@/lib/auth/password";
import { env } from "@/lib/env";
import { type MessageKey, t } from "@/lib/i18n";
import { supabaseBrowser } from "@/lib/supabase/browser";

export type LoginNotice =
  { kind: "cancelled"; provider: OAuthProvider } | { kind: "linkExpired" } | { kind: "failed" };

const PASSWORD_ERRORS: Partial<Record<PasswordOutcome, MessageKey>> = {
  "too-short": "auth.error.tooShort",
  "wrong-password": "auth.error.wrongPassword",
  "weak-password": "auth.error.weakPassword",
  "rate-limited": "auth.error.rateLimited",
  failed: "auth.error.failed",
};

function noticeText(notice: LoginNotice): string {
  switch (notice.kind) {
    case "cancelled":
      return t("auth.error.cancelled", { provider: t(`auth.provider.${notice.provider}`) });
    case "linkExpired":
      return t("auth.error.linkExpired");
    case "failed":
      return t("auth.error.failed");
  }
}

/** Callback URL for OAuth and email links; `next` rides along so the user lands where they meant. */
function callbackUrl(next: string | null, provider?: OAuthProvider): string {
  const url = new URL("/auth/callback", env.siteUrl);
  if (next) url.searchParams.set("next", next);
  if (provider) url.searchParams.set("provider", provider);
  return url.toString();
}

export function LoginForm({ next, notice }: { next: string | null; notice: LoginNotice | null }) {
  const [busy, setBusy] = useState<"password" | OAuthProvider | null>(null);
  const [banner, setBanner] = useState<string | null>(notice ? noticeText(notice) : null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email")).trim();
    setBusy("password");
    setBanner(null);
    setPasswordError(null);
    const outcome = await continueWithPassword(supabaseBrowser().auth, {
      email,
      password: String(form.get("password")),
      emailRedirectTo: callbackUrl(next),
    }).catch((): PasswordOutcome => "failed");
    if (outcome === "signed-in") {
      window.location.assign(continuePath(next));
      return;
    }
    setBusy(null);
    if (outcome === "check-email") {
      setSentTo(email);
      return;
    }
    const key = PASSWORD_ERRORS[outcome];
    setPasswordError(key ? t(key) : null);
  }

  async function signInWith(provider: OAuthProvider) {
    setBusy(provider);
    setBanner(null);
    const { error } = await supabaseBrowser().auth.signInWithOAuth({
      provider,
      options: { redirectTo: callbackUrl(next, provider), scopes: OAUTH_SCOPES[provider] },
    });
    // On success the browser is already leaving for the provider.
    if (error) {
      setBusy(null);
      setBanner(t("auth.error.failed"));
    }
  }

  if (sentTo) {
    return (
      <div className="flex flex-col gap-5" role="status">
        <span
          aria-hidden="true"
          className="flex size-12 items-center justify-center rounded-[14px] bg-evergreen-soft text-evergreen"
        >
          <EnvelopeSimpleIcon className="size-6" />
        </span>
        <div className="flex flex-col gap-2">
          <h1 className="type-heading lg:text-[30px] lg:leading-9">{t("auth.checkEmailTitle")}</h1>
          <p className="text-[15px] leading-6 text-ink-muted">
            {t("auth.checkEmailBody", { email: sentTo })}
          </p>
        </div>
        <Button variant="secondary" className="self-start" onClick={() => setSentTo(null)}>
          {t("auth.useDifferentEmail")}
        </Button>
      </div>
    );
  }

  const [legalBefore = "", legalMiddle = "", legalAfter = ""] =
    t("auth.legal").split(/\{terms\}|\{privacy\}/);

  return (
    <div className="flex flex-col gap-7">
      <div className="flex flex-col gap-2">
        <h1 className="type-heading lg:text-[30px] lg:leading-9">{t("auth.signInTitle")}</h1>
        <p className="text-[15px] leading-6 text-ink-muted">{t("auth.signInIntro")}</p>
      </div>

      {banner && (
        <div
          role="alert"
          className="flex gap-2.5 rounded-md border border-signal-gap bg-surface-raised px-3.5 py-3 text-[14px] leading-5 text-ink"
        >
          <WarningCircleIcon aria-hidden="true" className="mt-px size-5 shrink-0 text-signal-gap" />
          <span>{banner}</span>
        </div>
      )}

      <div className="flex flex-col gap-3">
        <Button
          variant="secondary"
          size="lg"
          className="w-full gap-3"
          icon={<GoogleMark />}
          loading={busy === "google"}
          disabled={busy !== null}
          onClick={() => signInWith("google")}
        >
          {t("auth.continueWithGoogle")}
        </Button>
        <Button
          variant="secondary"
          size="lg"
          className="w-full gap-3"
          icon={<MicrosoftMark />}
          loading={busy === "azure"}
          disabled={busy !== null}
          onClick={() => signInWith("azure")}
        >
          {t("auth.continueWithMicrosoft")}
        </Button>
      </div>

      <div className="flex items-center gap-4 text-[13px] text-ink-muted">
        <span aria-hidden="true" className="h-px flex-1 bg-line" />
        <span>{t("auth.orUseEmail")}</span>
        <span aria-hidden="true" className="h-px flex-1 bg-line" />
      </div>

      <form className="flex flex-col gap-[18px]" onSubmit={submit}>
        <Field label={t("auth.email")} required>
          <Input
            name="email"
            type="email"
            autoComplete="email"
            inputMode="email"
            placeholder={t("auth.emailPlaceholder")}
            required
          />
        </Field>
        <Field label={t("auth.password")} error={passwordError} required>
          <Input
            name="password"
            type="password"
            autoComplete="current-password"
            placeholder={t("auth.passwordPlaceholder")}
            required
          />
        </Field>
        <Button
          type="submit"
          size="lg"
          className="mt-1.5 w-full"
          loading={busy === "password"}
          disabled={busy !== null}
        >
          {t("auth.continue")}
        </Button>
      </form>

      <p className="text-[13px] leading-[1.6] text-ink-muted">
        {legalBefore}
        <Link href="/terms" className="text-evergreen underline hover:text-persimmon">
          {t("auth.terms")}
        </Link>
        {legalMiddle}
        <Link href="/privacy" className="text-evergreen underline hover:text-persimmon">
          {t("auth.privacy")}
        </Link>
        {legalAfter}
      </p>
    </div>
  );
}
