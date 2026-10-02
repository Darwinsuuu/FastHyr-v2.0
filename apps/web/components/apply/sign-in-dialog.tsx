"use client";

import { LockSimpleIcon, WarningCircleIcon } from "@phosphor-icons/react";
import Link from "next/link";
import { useState } from "react";

import { CompanyMark } from "@/components/apply/company-mark";
import { GoogleMark, MicrosoftMark } from "@/components/auth/provider-marks";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import type { PublicPipeline } from "@/lib/apply";
import type { SignInIntent, SignInProblem } from "@/lib/apply/session";
import type { OAuthProvider } from "@/lib/auth/flow";
import { t } from "@/lib/i18n";

const linkClass = "text-evergreen underline hover:text-persimmon";

/**
 * Sign in to apply (frame Apply): Google or Microsoft only (ADR-014), what the account is used for,
 * and where to go without either account.
 */
export function SignInDialog({
  open,
  onOpenChange,
  pipeline,
  intent,
  problem,
  onSignIn,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  pipeline: PublicPipeline;
  intent: SignInIntent;
  /** Why the last attempt came back without a session. */
  problem: SignInProblem | null;
  /** Starts the round trip; false when it couldn't leave for the provider. */
  onSignIn: (provider: OAuthProvider, intent: SignInIntent) => Promise<boolean>;
}) {
  const { company } = pipeline;
  const [busy, setBusy] = useState<OAuthProvider | null>(null);
  const [failed, setFailed] = useState(false);

  async function signIn(provider: OAuthProvider) {
    setBusy(provider);
    setFailed(false);
    if (!(await onSignIn(provider, intent))) {
      setBusy(null);
      setFailed(true);
    }
  }

  const alert = failed ? t("apply.signIn.failed") : problem ? t(`apply.signIn.${problem}`) : null;
  const [legalBefore = "", legalMiddle = "", legalAfter = ""] =
    t("apply.signIn.legal").split(/\{terms\}|\{privacy\}/);

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setFailed(false);
        onOpenChange(next);
      }}
      size="sm"
      leading={<CompanyMark company={company} size="lg" />}
      title={intent === "apply" ? t("apply.signIn.titleApply") : t("apply.signIn.titleBrowse")}
      description={
        intent === "apply"
          ? t("apply.signIn.bodyApply", { title: pipeline.title, company: company.name })
          : t("apply.signIn.bodyBrowse")
      }
    >
      <div className="flex flex-col gap-5 pb-5 md:pb-5">
        {alert && (
          <p
            role="alert"
            className="flex gap-2.5 rounded-md border border-signal-gap bg-surface-raised px-3.5 py-3 text-[14px] leading-5"
          >
            <WarningCircleIcon
              aria-hidden="true"
              className="mt-px size-[18px] shrink-0 text-signal-gap"
            />
            {alert}
          </p>
        )}
        <div className="flex flex-col gap-2.5">
          <Button
            variant="secondary"
            side="candidate"
            size="lg"
            icon={<GoogleMark />}
            loading={busy === "google"}
            disabled={busy !== null && busy !== "google"}
            onClick={() => void signIn("google")}
          >
            {t("apply.signIn.google")}
          </Button>
          <Button
            variant="secondary"
            side="candidate"
            size="lg"
            icon={<MicrosoftMark />}
            loading={busy === "azure"}
            disabled={busy !== null && busy !== "azure"}
            onClick={() => void signIn("azure")}
          >
            {t("apply.signIn.microsoft")}
          </Button>
        </div>
        <p className="flex gap-2.5 rounded-md bg-surface px-3.5 py-3 text-[13px] leading-5 text-ink-muted">
          <LockSimpleIcon aria-hidden="true" className="mt-px size-4 shrink-0 text-evergreen" />
          {t("apply.signIn.noPassword")}
        </p>
        <NoAccountNote company={company} />
        <p className="text-center text-[12px] leading-[18px] text-ink-muted">
          {legalBefore}
          <Link href="/terms" className={linkClass}>
            {t("apply.signIn.terms")}
          </Link>
          {legalMiddle}
          <Link href="/privacy" className={linkClass}>
            {t("apply.signIn.privacy")}
          </Link>
          {legalAfter}
        </p>
      </div>
    </Dialog>
  );
}

/** Candidates without Google or Microsoft apply through the employer instead (ADR-014). */
function NoAccountNote({ company }: { company: PublicPipeline["company"] }) {
  if (!company.website) {
    return (
      <p className="text-[13px] leading-5 text-ink-muted">
        {t("apply.signIn.noAccount", { company: company.name })}
      </p>
    );
  }
  const [before = "", after = ""] = t("apply.signIn.noAccountWebsite", {
    company: company.name,
  }).split("{website}");
  return (
    <p className="text-[13px] leading-5 text-ink-muted">
      {before}
      <a href={company.website} target="_blank" rel="noopener noreferrer" className={linkClass}>
        {t("apply.signIn.theirWebsite")}
        <span className="sr-only"> {t("apply.company.newTab")}</span>
      </a>
      {after}
    </p>
  );
}
