"use client";

import { CaretDownIcon, SignOutIcon } from "@phosphor-icons/react";
import { forwardRef, type ButtonHTMLAttributes, useState } from "react";

import { useApplySession } from "@/components/apply/apply-session";
import { ShellMenu } from "@/components/app-shell/shell-menu";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import type { Candidate } from "@/lib/apply/session";
import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";

/** The apply page header's account control: Sign in, or the signed-in candidate's menu. */
export function CandidateMenu() {
  const { candidate, openSignIn, signOut } = useApplySession();
  const [open, setOpen] = useState(false);

  if (!candidate) {
    return (
      <Button variant="secondary" side="candidate" onClick={openSignIn}>
        {t("apply.signIn.open")}
      </Button>
    );
  }

  return (
    <ShellMenu
      title={t("apply.account.menu")}
      side="bottom"
      align="end"
      open={open}
      onOpenChange={setOpen}
      className="w-[260px]"
      header={
        <div className="mb-1 flex flex-col gap-0.5 border-b border-line px-2.5 pt-2.5 pb-3">
          <span className="truncate text-[15px] font-semibold md:text-[14px]">
            {candidate.name}
          </span>
          <span className="truncate text-[13px] text-ink-muted md:text-[12px]">
            {candidate.email}
          </span>
          <span className="text-[13px] text-ink-muted md:text-[12px]">
            {t("apply.account.signedInWith", {
              provider: t(`auth.provider.${candidate.provider}`),
            })}
          </span>
        </div>
      }
      entries={[
        {
          id: "sign-out",
          label: t("apply.account.signOut"),
          leading: <SignOutIcon aria-hidden="true" className="size-[18px] shrink-0" />,
          onSelect: () => void signOut(),
        },
      ]}
      trigger={<AccountButton candidate={candidate} open={open} />}
    />
  );
}

interface AccountButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  candidate: Candidate;
  open: boolean;
}

/** Avatar on phones; avatar, name and caret from `sm` (frame Apply). */
const AccountButton = forwardRef<HTMLButtonElement, AccountButtonProps>(function AccountButton(
  { candidate, open, className, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      aria-label={t("apply.account.menuFor", { name: candidate.name })}
      className={cn(
        "flex min-h-11 shrink-0 items-center gap-2.5 rounded-pill border border-line p-1 text-[14px] font-semibold text-ink",
        "transition-colors duration-200 ease-out hover:bg-surface-sunk sm:min-h-10 sm:py-1 sm:pr-3 sm:pl-1.5",
        open ? "bg-surface-sunk" : "bg-surface-raised",
        className,
      )}
      {...props}
    >
      <Avatar id={candidate.id} name={candidate.name} size="sm" />
      <span className="hidden max-w-[160px] truncate sm:inline">{candidate.name}</span>
      <CaretDownIcon aria-hidden="true" className="hidden size-3.5 text-ink-muted sm:inline" />
    </button>
  );
});
