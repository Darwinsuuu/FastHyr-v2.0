"use client";

import { CaretUpDownIcon, SignOutIcon } from "@phosphor-icons/react";
import { forwardRef, type ButtonHTMLAttributes, useState } from "react";

import { logOut } from "@/components/auth/log-out-button";
import { useShell } from "@/components/app-shell/shell-context";
import { ShellMenu } from "@/components/app-shell/shell-menu";
import { Avatar } from "@/components/ui/avatar";
import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";

/** The signed-in user: name, role in this workspace, Log out. "User profile" is AUTH-005. */
export function UserMenu({ variant }: { variant: "sidebar" | "topbar" }) {
  const { user, workspace } = useShell();
  const [open, setOpen] = useState(false);

  return (
    <ShellMenu
      title={t("shell.accountMenu")}
      side={variant === "sidebar" ? "right" : "bottom"}
      align="end"
      open={open}
      onOpenChange={setOpen}
      className="w-[248px]"
      header={
        <div className="mb-1 flex flex-col border-b border-line px-2.5 pt-2.5 pb-3">
          <span className="truncate text-[15px] font-semibold md:text-[14px]">{user.name}</span>
          <span className="truncate text-[13px] text-ink-muted md:text-[12px]">
            {t("shell.roleInWorkspace", {
              role: t(`app.role.${workspace.role}`),
              workspace: workspace.name,
            })}
          </span>
        </div>
      }
      entries={[
        {
          id: "log-out",
          label: t("auth.logOut"),
          leading: <SignOutIcon aria-hidden="true" className="size-[18px] shrink-0" />,
          destructive: true,
          onSelect: () => void logOut(),
        },
      ]}
      trigger={<UserButton variant={variant} open={open} />}
    />
  );
}

interface UserButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant: "sidebar" | "topbar";
  open: boolean;
}

const UserButton = forwardRef<HTMLButtonElement, UserButtonProps>(function UserButton(
  { variant, open, className, ...props },
  ref,
) {
  const { user } = useShell();
  if (variant === "topbar") {
    return (
      <button
        ref={ref}
        type="button"
        aria-label={t("shell.accountMenu")}
        className={cn(
          "flex size-11 shrink-0 items-center justify-center rounded-pill hover:bg-surface-sunk",
          open && "bg-surface-sunk",
          className,
        )}
        {...props}
      >
        <Avatar id={user.id} name={user.name} src={user.avatarUrl} />
      </button>
    );
  }
  return (
    <button
      ref={ref}
      type="button"
      aria-label={t("shell.accountMenuFor", { name: user.name })}
      className={cn(
        "flex w-full shrink-0 items-center gap-2.5 rounded-[12px] border border-line px-2.5 py-2 text-left text-ink",
        "transition-colors duration-200 ease-out hover:bg-surface-sunk",
        open ? "bg-surface-sunk" : "bg-surface-raised",
        className,
      )}
      {...props}
    >
      <Avatar id={user.id} name={user.name} src={user.avatarUrl} />
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="truncate text-[14px] leading-[18px] font-semibold">{user.name}</span>
        {user.email !== user.name && (
          <span className="truncate text-[12px] leading-4 text-ink-muted">{user.email}</span>
        )}
      </span>
      <CaretUpDownIcon aria-hidden="true" className="size-4 shrink-0 text-ink-muted" />
    </button>
  );
});
