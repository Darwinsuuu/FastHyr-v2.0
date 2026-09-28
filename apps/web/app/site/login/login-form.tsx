"use client";

import { type FormEvent, useState } from "react";

import { env } from "@/lib/env";
import { safeNextPath } from "@/lib/hosts";
import { t } from "@/lib/i18n";
import { supabaseBrowser } from "@/lib/supabase/browser";

// Microsoft returns no email or name unless these scopes are asked for (FND-002 log).
const OAUTH_SCOPES = { google: undefined, azure: "email profile" } as const;

export function LoginForm({ next, failed }: { next: string | null; failed: boolean }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(failed);
  const destination = new URL(safeNextPath(next), env.appUrl).toString();

  async function signInWithPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(false);
    const { error: signInError } = await supabaseBrowser().auth.signInWithPassword({
      email: String(form.get("email")),
      password: String(form.get("password")),
    });
    if (signInError) {
      setBusy(false);
      setError(true);
      return;
    }
    window.location.assign(destination);
  }

  async function signInWith(provider: keyof typeof OAUTH_SCOPES) {
    const callback = new URL("/auth/callback", env.siteUrl);
    callback.searchParams.set("next", safeNextPath(next));
    await supabaseBrowser().auth.signInWithOAuth({
      provider,
      options: { redirectTo: callback.toString(), scopes: OAUTH_SCOPES[provider] },
    });
  }

  const button = "type-body min-h-11 w-full rounded-md px-5 py-3 font-semibold disabled:opacity-60";

  return (
    <div className="mt-8 flex flex-col gap-4">
      <form className="flex flex-col gap-4" onSubmit={signInWithPassword}>
        <label className="flex flex-col gap-2">
          <span className="type-label text-ink-muted">{t("auth.email")}</span>
          <input
            name="email"
            type="email"
            autoComplete="email"
            required
            className="min-h-11 rounded-sm border border-line-strong bg-surface-raised px-3"
          />
        </label>
        <label className="flex flex-col gap-2">
          <span className="type-label text-ink-muted">{t("auth.password")}</span>
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
            className="min-h-11 rounded-sm border border-line-strong bg-surface-raised px-3"
          />
        </label>
        {error && (
          <p role="alert" className="type-body-sm text-signal-gap">
            {t("auth.signInFailed")}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className={`${button} bg-evergreen text-on-evergreen`}
        >
          {busy ? t("auth.signingIn") : t("auth.signIn")}
        </button>
      </form>
      <button
        type="button"
        onClick={() => signInWith("google")}
        className={`${button} border border-line-strong bg-surface-raised`}
      >
        {t("auth.continueWithGoogle")}
      </button>
      <button
        type="button"
        onClick={() => signInWith("azure")}
        className={`${button} border border-line-strong bg-surface-raised`}
      >
        {t("auth.continueWithMicrosoft")}
      </button>
    </div>
  );
}
