"use client";

import { CheckIcon, CopyIcon, EnvelopeSimpleIcon, InfoIcon } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { type ReactNode, type RefObject, useEffect, useState } from "react";

import { GoogleMark, MicrosoftMark } from "@/components/auth/provider-marks";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { type AccountDetails, type SignInMethod, accountDetails } from "@/lib/auth/account";
import { cn } from "@/lib/cn";
import { formatDate, formatDateTime } from "@/lib/format";
import { t } from "@/lib/i18n";
import { supabaseBrowser } from "@/lib/supabase/browser";

/** What the menu already knows, shown in the header while Auth answers. */
export interface ProfileDialogUser {
  id: string;
  name: string;
  avatarUrl: string | null;
}

const timeZone = () => Intl.DateTimeFormat().resolvedOptions().timeZone;

async function fetchAccount(): Promise<AccountDetails> {
  // getUser() asks the Auth server, so last sign-in and linked providers are current.
  const { data, error } = await supabaseBrowser().auth.getUser();
  if (error || !data.user) throw error ?? new Error("No signed-in user");
  return accountDetails(data.user);
}

/** The signed-in user's account (frame WorkspaceSelect, FR-AUTH-08). Read only. */
export function ProfileDialog({
  open,
  onOpenChange,
  user,
  returnFocusTo,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user: ProfileDialogUser;
  /** The account menu's button, since the menu item that opened the dialog is gone on close. */
  returnFocusTo?: RefObject<HTMLElement | null>;
}) {
  const account = useQuery({
    queryKey: ["auth", "account"],
    queryFn: fetchAccount,
    enabled: open,
    staleTime: 0,
    retry: false,
  });
  const name = account.data?.name ?? user.name;

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={name}
      description={t("auth.profile.subtitle")}
      returnFocusTo={returnFocusTo}
      leading={
        <Avatar
          id={user.id}
          name={name}
          src={account.data?.avatarUrl ?? user.avatarUrl}
          className="size-14 text-[20px] md:size-16 md:text-[22px]"
        />
      }
      footer={
        <Button variant="secondary" onClick={() => onOpenChange(false)}>
          {t("ui.close")}
        </Button>
      }
    >
      {account.data ? (
        <AccountFacts account={account.data} />
      ) : account.isError ? (
        <div className="flex flex-col items-start gap-3 pb-2">
          <p role="alert" className="type-body text-ink-muted">
            {t("auth.profile.loadFailed")}
          </p>
          <Button variant="secondary" size="sm" onClick={() => void account.refetch()}>
            {t("ui.tryAgain")}
          </Button>
        </div>
      ) : (
        <div
          aria-busy="true"
          aria-label={t("auth.profile.loading")}
          className="flex flex-col gap-3 pb-2"
        >
          {[0, 1, 2, 3, 4].map((row) => (
            <Skeleton key={row} className="h-11 rounded-md" />
          ))}
        </div>
      )}
    </Dialog>
  );
}

function AccountFacts({ account }: { account: AccountDetails }) {
  const zone = timeZone();
  return (
    <div className="flex flex-col gap-5 pb-2">
      <dl className="grid overflow-hidden rounded-md border border-line md:grid-cols-[150px_minmax(0,1fr)]">
        <Fact label={t("auth.profile.email")} first>
          <span className="flex flex-wrap items-center gap-2">
            <span className="break-all">{account.email}</span>
            {account.emailVerified ? (
              <Badge tone="evergreen" icon={<CheckIcon aria-hidden="true" weight="bold" />}>
                {t("auth.profile.verified")}
              </Badge>
            ) : (
              <Badge tone="watch">{t("auth.profile.notVerified")}</Badge>
            )}
          </span>
        </Fact>
        <Fact label={t("auth.profile.signsInWith")}>
          <span className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
            {account.methods.map((method) => (
              <span key={method} className="flex items-center gap-2">
                <MethodMark method={method} />
                {t(`auth.profile.method.${method}`)}
              </span>
            ))}
          </span>
        </Fact>
        {account.lastSignInAt && (
          <Fact label={t("auth.profile.lastSignedIn")}>
            {formatDateTime(account.lastSignInAt, zone)}
          </Fact>
        )}
        <Fact label={t("auth.profile.created")}>{formatDate(account.createdAt, zone)}</Fact>
        <Fact label={t("auth.profile.userId")} compact>
          <UserId id={account.id} />
        </Fact>
      </dl>
      <p className="flex gap-2.5 rounded-md bg-surface px-3.5 py-3 text-[13px] leading-[19px] text-ink-muted">
        <InfoIcon aria-hidden="true" className="mt-px size-4 shrink-0" />
        <span>
          {account.profileSource
            ? t("auth.profile.nameFrom", {
                provider: t(`auth.profile.method.${account.profileSource}`),
              })
            : t("auth.profile.nameFromEmail")}
        </span>
      </p>
    </div>
  );
}

/** One row: label over value on phones, label column beside the value from `md`. */
function Fact({
  label,
  children,
  first,
  compact,
}: {
  label: string;
  children: ReactNode;
  first?: boolean;
  compact?: boolean;
}) {
  return (
    <>
      <dt
        className={cn(
          "px-4 pt-3 text-[13px] leading-[18px] text-ink-muted md:bg-surface md:py-3.5",
          !first && "border-t border-line",
        )}
      >
        {label}
      </dt>
      <dd
        className={cn(
          "m-0 min-w-0 px-4 pt-1 pb-3 text-[14px] leading-5 text-ink",
          compact ? "md:py-2.5" : "md:py-3.5",
          !first && "md:border-t md:border-line",
        )}
      >
        {children}
      </dd>
    </>
  );
}

function MethodMark({ method }: { method: SignInMethod }) {
  if (method === "google") return <GoogleMark />;
  if (method === "microsoft") return <MicrosoftMark />;
  return <EnvelopeSimpleIcon aria-hidden="true" className="size-5 shrink-0 text-ink-muted" />;
}

function UserId({ id }: { id: string }) {
  // Idle, "copied" for 2 s, or "failed" until the next try. No toast: /workspaces has no ToastProvider.
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");
  const copied = copyState === "copied";

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopyState("idle"), 2000);
    return () => clearTimeout(timer);
  }, [copied]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(id);
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
  }

  return (
    <span className="flex flex-col gap-1.5">
      <span className="flex items-center justify-between gap-2.5">
        <span data-testid="profile-user-id" className="truncate font-mono text-[12px] leading-5">
          {id}
        </span>
        <Button
          variant="secondary"
          size="sm"
          aria-label={copied ? t("auth.profile.copied") : t("auth.profile.copyId")}
          onClick={() => void copy()}
          className="shrink-0"
        >
          {copied ? (
            <CheckIcon aria-hidden="true" weight="bold" className="size-4" />
          ) : (
            <CopyIcon aria-hidden="true" className="size-4" />
          )}
          {copied ? t("auth.profile.copied") : t("auth.profile.copy")}
        </Button>
      </span>
      <span
        aria-live="polite"
        className={
          copyState === "failed" ? "text-[13px] leading-[18px] text-signal-gap" : "sr-only"
        }
      >
        {copied ? t("auth.profile.copiedAnnounce") : ""}
        {copyState === "failed" ? t("auth.profile.copyFailed") : ""}
      </span>
    </span>
  );
}
