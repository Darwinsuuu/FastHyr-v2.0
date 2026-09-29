"use client";

import { EnvelopeSimpleIcon, InfoIcon, KeyIcon } from "@phosphor-icons/react";
import { type FormEvent, type ReactNode, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { isValidEmail, requestPasswordReset } from "@/lib/auth/recovery";
import { useCooldown } from "@/lib/hooks/use-cooldown";
import { t } from "@/lib/i18n";
import { supabaseBrowser } from "@/lib/supabase/browser";

function DialogTitle({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <span className="flex items-center gap-3.5">
      <span
        aria-hidden="true"
        className="flex size-12 shrink-0 items-center justify-center rounded-[14px] bg-evergreen-soft text-evergreen"
      >
        {icon}
      </span>
      <span className="font-display text-[24px] leading-[30px] font-[560]">{children}</span>
    </span>
  );
}

/**
 * The forgot-password modal from frame EmployerLogin (FR-AUTH-02): form → sending → sent, with a
 * 60 s resend countdown. "Back to sign in" closes it, or runs `onBackToSignIn` when given.
 */
export function ForgotPasswordDialog({
  open,
  onOpenChange,
  initialEmail = "",
  onBackToSignIn,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialEmail?: string;
  onBackToSignIn?: () => void;
}) {
  const [email, setEmail] = useState(initialEmail);
  const [tried, setTried] = useState(false);
  const [sending, setSending] = useState(false);
  const [failed, setFailed] = useState(false);
  const [sentAt, setSentAt] = useState<number | null>(null);
  const wait = useCooldown(sentAt);

  const [lastInitial, setLastInitial] = useState(initialEmail);
  if (open && initialEmail !== lastInitial) {
    // Opening again picks up what's now in the sign-in form.
    setLastInitial(initialEmail);
    if (sentAt === null) setEmail(initialEmail);
  }

  const emailError =
    tried && !isValidEmail(email)
      ? t(email.trim() ? "auth.forgot.emailInvalid" : "auth.forgot.emailRequired")
      : null;

  async function send() {
    setSending(true);
    setFailed(false);
    const outcome = await requestPasswordReset(supabaseBrowser().auth, email);
    setSending(false);
    if (outcome === "failed") {
      setFailed(true);
      return;
    }
    setSentAt(Date.now());
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTried(true);
    if (sending || !isValidEmail(email)) return;
    void send();
  }

  function changeOpen(next: boolean) {
    onOpenChange(next);
    if (!next) {
      // Start over next time; a pending countdown restarts with the next send.
      setSentAt(null);
      setTried(false);
      setFailed(false);
    }
  }

  const back = onBackToSignIn ?? (() => changeOpen(false));
  const sent = sentAt !== null;
  const [sentBefore = "", sentAfter = ""] = t("auth.forgot.sentBody").split("{email}");

  return (
    <Dialog
      open={open}
      onOpenChange={changeOpen}
      size="sm"
      title={
        sent ? (
          <DialogTitle icon={<EnvelopeSimpleIcon className="size-6" />}>
            {t("auth.forgot.sentTitle")}
          </DialogTitle>
        ) : (
          <DialogTitle icon={<KeyIcon className="size-6" />}>{t("auth.forgot.title")}</DialogTitle>
        )
      }
      footer={
        sent ? (
          <div className="flex flex-col-reverse gap-2 md:flex-1 md:flex-row md:items-center md:justify-between">
            <Button
              variant="quiet"
              className="md:-ml-5"
              disabled={wait > 0}
              loading={sending}
              onClick={() => void send()}
            >
              {wait > 0 ? t("auth.resendLinkIn", { seconds: wait }) : t("auth.resendLink")}
            </Button>
            <Button onClick={back}>{t("auth.forgot.backToSignIn")}</Button>
          </div>
        ) : (
          <>
            <Button variant="secondary" onClick={back}>
              {t("auth.forgot.backToSignIn")}
            </Button>
            <Button type="submit" form="forgot-password" loading={sending}>
              {t("auth.forgot.send")}
            </Button>
          </>
        )
      }
    >
      {sent ? (
        <div className="flex flex-col gap-5">
          <p role="status" className="text-[15px] leading-[23px] text-ink">
            {sentBefore}
            <strong className="font-[650] break-all">{email.trim()}</strong>
            {sentAfter}
          </p>
          <ul className="flex list-disc flex-col gap-1.5 rounded-md bg-surface py-3.5 pr-4 pl-[34px] text-[14px] leading-5 text-ink">
            <li>{t("auth.forgot.sentFrom")}</li>
            <li>{t("auth.forgot.sentDevice")}</li>
          </ul>
          {failed && (
            <p role="alert" className="text-[13px] leading-[18px] font-semibold text-signal-gap">
              {t("auth.forgot.failed")}
            </p>
          )}
        </div>
      ) : (
        <form id="forgot-password" noValidate className="flex flex-col gap-5" onSubmit={submit}>
          <p className="text-[15px] leading-[23px] text-ink-muted">{t("auth.forgot.intro")}</p>
          <Field
            label={t("auth.email")}
            hint={emailError ? undefined : t("auth.forgot.emailHint")}
            error={emailError ?? (failed ? t("auth.forgot.failed") : null)}
          >
            <Input
              name="email"
              type="email"
              autoComplete="email"
              inputMode="email"
              placeholder={t("auth.emailPlaceholder")}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </Field>
          <p className="flex gap-2.5 rounded-md bg-surface px-3.5 py-3 text-[13px] leading-[19px] text-ink-muted">
            <InfoIcon aria-hidden="true" className="mt-px size-4 shrink-0" />
            <span>{t("auth.forgot.oauthNote")}</span>
          </p>
        </form>
      )}
    </Dialog>
  );
}
