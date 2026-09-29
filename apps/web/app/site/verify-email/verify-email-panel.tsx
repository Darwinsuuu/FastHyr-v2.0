"use client";

import { EnvelopeSimpleIcon } from "@phosphor-icons/react";
import { useEffect, useState, useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import { verifyEmailRedirect } from "@/lib/auth/links";
import {
  forgetPendingVerification,
  parsePendingVerification,
  readPendingVerificationRaw,
  rememberPendingVerification,
  tabStorage,
} from "@/lib/auth/pending-verification";
import { env } from "@/lib/env";
import { useCooldown } from "@/lib/hooks/use-cooldown";
import { type MessageKey, t } from "@/lib/i18n";
import { supabaseBrowser } from "@/lib/supabase/browser";

function subscribeToNothing() {
  // sessionStorage doesn't notify the tab that wrote it; the panel updates its own state instead.
  return () => {};
}

export function VerifyEmailPanel({
  next,
  sessionEmail,
}: {
  next: string | null;
  sessionEmail: string | null;
}) {
  // undefined on the server, where the tab's storage doesn't exist.
  const raw = useSyncExternalStore(
    subscribeToNothing,
    () => readPendingVerificationRaw(tabStorage()),
    () => undefined,
  );
  const stored = raw === undefined ? undefined : parsePendingVerification(raw);
  const email = sessionEmail ?? stored?.email ?? null;
  const [resentAt, setResentAt] = useState<number | null>(null);
  // The stored send time only counts for the same address.
  const sentAt = resentAt ?? (stored && stored.email === email ? stored.sentAt : null);
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState<{ key: MessageKey; error: boolean } | null>(null);
  const wait = useCooldown(sentAt);

  const missing = raw !== undefined && !email;
  useEffect(() => {
    // Nothing to verify in this tab (opened directly, or storage is off): back to sign in.
    if (missing) window.location.replace(new URL("/login", env.siteUrl).toString());
  }, [missing]);

  async function resend() {
    if (!email) return;
    setSending(true);
    setNotice(null);
    const { error } = await supabaseBrowser()
      .auth.resend({
        type: "signup",
        email,
        options: { emailRedirectTo: verifyEmailRedirect(next) },
      })
      .catch(() => ({ error: { code: "network" } }));
    setSending(false);
    if (!error) {
      const now = Date.now();
      rememberPendingVerification(tabStorage(), { email, sentAt: now });
      setResentAt(now);
      setNotice({ key: "auth.verify.resent", error: false });
      return;
    }
    const rateLimited =
      error.code === "over_email_send_rate_limit" || error.code === "over_request_rate_limit";
    setNotice({ key: rateLimited ? "auth.error.rateLimited" : "auth.verify.failed", error: true });
  }

  async function switchEmail() {
    forgetPendingVerification(tabStorage());
    await supabaseBrowser()
      .auth.signOut({ scope: "local" })
      .catch(() => undefined);
    window.location.assign(new URL("/login", env.siteUrl).toString());
  }

  if (!email) return null;

  const [bodyBefore = "", bodyAfter = ""] = t("auth.checkEmailBody").split("{email}");

  return (
    <div className="flex flex-col gap-5">
      <span
        aria-hidden="true"
        className="flex size-12 items-center justify-center rounded-[14px] bg-evergreen-soft text-evergreen"
      >
        <EnvelopeSimpleIcon className="size-6" />
      </span>
      <div className="flex flex-col gap-2">
        <h1 className="type-heading lg:text-[30px] lg:leading-9">{t("auth.checkEmailTitle")}</h1>
        <p className="text-[15px] leading-6 text-ink-muted">
          {bodyBefore}
          <strong className="font-[650] break-all text-ink">{email}</strong>
          {bodyAfter}
        </p>
      </div>
      {notice && (
        <p
          role={notice.error ? "alert" : "status"}
          className={
            notice.error
              ? "text-[13px] leading-[18px] font-semibold text-signal-gap"
              : "text-[14px] leading-5 text-ink"
          }
        >
          {t(notice.key)}
        </p>
      )}
      <div className="flex flex-col gap-3 sm:flex-row">
        <Button
          variant="secondary"
          disabled={wait > 0}
          loading={sending}
          onClick={() => void resend()}
        >
          {wait > 0 ? t("auth.resendLinkIn", { seconds: wait }) : t("auth.resendLink")}
        </Button>
        <Button variant="quiet" onClick={() => void switchEmail()}>
          {t("auth.useDifferentEmail")}
        </Button>
      </div>
    </div>
  );
}
