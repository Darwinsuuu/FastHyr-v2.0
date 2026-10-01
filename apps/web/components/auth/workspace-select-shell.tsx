"use client";

import { CaretDownIcon, SignOutIcon, UserCircleIcon } from "@phosphor-icons/react";
import Link from "next/link";
import { type ReactNode, useRef, useState } from "react";

import { logOut } from "@/components/auth/log-out-button";
import { ProfileDialog } from "@/components/auth/profile-dialog";
import { TurnMark } from "@/components/brand/turn-mark";
import { Avatar } from "@/components/ui/avatar";
import { Menu } from "@/components/ui/menu";
import type { ClaimsUser } from "@/lib/auth/claims";
import { t } from "@/lib/i18n";

/**
 * The page around Choose workspace and Join a workspace (frame WorkspaceSelect): brand mark,
 * account menu with User profile and Log out, and the decorative shapes on large screens.
 */
export function WorkspaceSelectShell({
  user,
  children,
}: {
  user: ClaimsUser;
  children: ReactNode;
}) {
  const displayName = user.fullName || user.email;
  const [profileOpen, setProfileOpen] = useState(false);
  const accountButton = useRef<HTMLButtonElement>(null);

  return (
    <div className="relative flex min-h-dvh flex-col overflow-hidden bg-surface">
      <svg
        viewBox="0 0 32 32"
        aria-hidden="true"
        className="pointer-events-none absolute -right-[140px] -bottom-[180px] hidden size-[520px] opacity-35 lg:block"
      >
        <ellipse cx="10" cy="13" rx="10" ry="13" className="fill-sage" />
        <ellipse cx="22" cy="19" rx="8" ry="10" className="fill-persimmon-soft" />
      </svg>

      <header className="page-gutter relative flex h-16 shrink-0 items-center justify-between gap-4 md:h-[72px]">
        <Link href="/" aria-label={t("auth.homeLink")} className="flex items-center gap-2.5">
          <TurnMark size={28} />
          <span className="font-display text-[20px] font-semibold tracking-[-0.02em]">
            {t("site.name")}
          </span>
        </Link>
        <Menu
          title={displayName}
          items={[
            {
              label: t("auth.profile.open"),
              icon: <UserCircleIcon aria-hidden="true" />,
              onSelect: () => setProfileOpen(true),
            },
            {
              label: t("auth.logOut"),
              icon: <SignOutIcon aria-hidden="true" />,
              destructive: true,
              onSelect: () => void logOut(),
            },
          ]}
          trigger={
            <button
              ref={accountButton}
              type="button"
              aria-label={t("workspaces.account")}
              className="flex min-h-11 items-center gap-2.5 rounded-pill border border-line bg-surface-raised py-1.5 pr-2.5 pl-1.5 text-ink hover:bg-surface-sunk data-[state=open]:bg-surface-sunk"
            >
              <Avatar id={user.id} name={displayName} src={user.avatarUrl} size="md" />
              <span className="hidden max-w-[200px] truncate text-[14px] font-semibold md:block">
                {displayName}
              </span>
              <CaretDownIcon aria-hidden="true" className="size-4 text-ink-muted" />
            </button>
          }
        />
      </header>

      {children}

      <ProfileDialog
        open={profileOpen}
        onOpenChange={setProfileOpen}
        user={{ id: user.id, name: displayName, avatarUrl: user.avatarUrl }}
        returnFocusTo={accountButton}
      />
    </div>
  );
}

/** "Signed in as {email} · Not you? Log out", under the cards. */
export function SignedInAs({ email, onLogOut }: { email: string; onLogOut?: () => void }) {
  return (
    <p className="text-center text-[14px] text-ink-muted">
      {t("workspaces.signedInAs")} <span className="font-semibold break-all text-ink">{email}</span>{" "}
      ·{" "}
      <button
        type="button"
        onClick={onLogOut ?? (() => void logOut())}
        className="font-semibold text-evergreen underline-offset-2 hover:underline"
      >
        {t("workspaces.notYou")}
      </button>
    </p>
  );
}
