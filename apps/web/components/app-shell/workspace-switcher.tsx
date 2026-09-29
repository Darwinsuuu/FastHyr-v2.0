"use client";

import { CaretUpDownIcon, PlusIcon, SignInIcon } from "@phosphor-icons/react";
import { usePathname } from "next/navigation";
import { forwardRef, type ButtonHTMLAttributes, type ReactNode, useState } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { ShellMenu, type ShellMenuEntry } from "@/components/app-shell/shell-menu";
import { WorkspaceAvatar } from "@/components/ui/avatar";
import { useToast } from "@/components/ui/toast";
import { useSwitchWorkspace } from "@/lib/api/provider";
import { switchDestination } from "@/lib/app-nav";
import { cn } from "@/lib/cn";
import { env } from "@/lib/env";
import { plural, t } from "@/lib/i18n";

function DashedTile({ children }: { children: ReactNode }) {
  return (
    <span
      aria-hidden="true"
      className="flex size-7 shrink-0 items-center justify-center rounded-[8px] border border-dashed border-line-strong text-evergreen [&>svg]:size-4"
    >
      {children}
    </span>
  );
}

/**
 * The workspace switcher (FR-AUTH-07): every workspace with the user's role and member count,
 * then Create and Join, which open Choose workspace on the site host.
 */
export function WorkspaceSwitcher({ variant }: { variant: "sidebar" | "topbar" }) {
  const { workspace, workspaces } = useShell();
  const pathname = usePathname();
  const switchWorkspace = useSwitchWorkspace();
  const toast = useToast();
  const [open, setOpen] = useState(false);

  const choose = async (id: string) => {
    const target = workspaces.find((row) => row.id === id);
    if (!target || target.id === workspace.id) return;
    try {
      await switchWorkspace(target.id);
      // A full load: every page starts clean in the new workspace.
      window.location.assign(switchDestination(pathname, target.role));
    } catch {
      toast({ tone: "error", title: t("shell.switchFailed") });
    }
  };
  const chooseWorkspacePage = () =>
    window.location.assign(new URL("/workspaces", env.siteUrl).toString());

  const entries: ShellMenuEntry[] = [
    ...workspaces.map((row) => ({
      id: row.id,
      label: row.name,
      description: `${t(`app.role.${row.role}`)} · ${plural("app.memberCount", row.memberCount)}`,
      leading: (
        <WorkspaceAvatar
          name={row.name}
          size="sm"
          className={row.id === workspace.id ? undefined : "bg-sage text-evergreen"}
        />
      ),
      radio: true,
      onSelect: () => void choose(row.id),
    })),
    "separator",
    {
      id: "create",
      label: t("shell.createWorkspace"),
      description: t("shell.createWorkspaceHint"),
      leading: (
        <DashedTile>
          <PlusIcon />
        </DashedTile>
      ),
      onSelect: chooseWorkspacePage,
    },
    {
      id: "join",
      label: t("shell.joinWorkspace"),
      description: t("shell.joinWorkspaceHint"),
      leading: (
        <DashedTile>
          <SignInIcon />
        </DashedTile>
      ),
      onSelect: chooseWorkspacePage,
    },
  ];

  return (
    <ShellMenu
      title={t("shell.workspacesMenu")}
      caption={t("shell.yourWorkspaces")}
      entries={entries}
      radioValue={workspace.id}
      open={open}
      onOpenChange={setOpen}
      trigger={<SwitcherButton variant={variant} name={workspace.name} open={open} />}
    />
  );
}

interface SwitcherButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant: "sidebar" | "topbar";
  name: string;
  open: boolean;
}

const SwitcherButton = forwardRef<HTMLButtonElement, SwitcherButtonProps>(function SwitcherButton(
  { variant, name, open, className, ...props },
  ref,
) {
  if (variant === "topbar") {
    return (
      <button
        ref={ref}
        type="button"
        aria-label={t("shell.switchWorkspace", { name })}
        className={cn(
          "flex h-11 min-w-0 items-center gap-2 rounded-[10px] px-2 text-left text-ink hover:bg-surface-sunk",
          open && "bg-surface-sunk",
          className,
        )}
        {...props}
      >
        <WorkspaceAvatar name={name} size="sm" />
        <span className="truncate text-[15px] font-[650]">{name}</span>
        <CaretUpDownIcon aria-hidden="true" className="size-4 shrink-0 text-ink-muted" />
      </button>
    );
  }
  return (
    <button
      ref={ref}
      type="button"
      aria-label={t("shell.switchWorkspace", { name })}
      className={cn(
        "flex w-full shrink-0 items-center gap-2.5 rounded-[12px] border border-line px-2.5 py-2 text-left text-ink",
        "transition-colors duration-200 ease-out hover:bg-surface-sunk",
        open ? "bg-surface-sunk" : "bg-surface-raised",
        className,
      )}
      {...props}
    >
      <WorkspaceAvatar name={name} className="size-8 text-[14px]" />
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="text-[11px] font-[650] tracking-[0.06em] text-ink-muted uppercase">
          {t("shell.workspace")}
        </span>
        <span className="truncate text-[14px] leading-[18px] font-[650]">{name}</span>
      </span>
      <CaretUpDownIcon aria-hidden="true" className="size-4 shrink-0 text-ink-muted" />
    </button>
  );
});
