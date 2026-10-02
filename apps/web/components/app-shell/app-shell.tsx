"use client";

import { ListIcon, XIcon } from "@phosphor-icons/react";
import * as RadixDialog from "@radix-ui/react-dialog";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ReactNode, useEffect, useMemo, useState } from "react";

import { TurnMark } from "@/components/brand/turn-mark";
import { type ShellState, ShellContext } from "@/components/app-shell/shell-context";
import { SidebarNav } from "@/components/app-shell/sidebar-nav";
import { UserMenu } from "@/components/app-shell/user-menu";
import { WorkspaceSwitcher } from "@/components/app-shell/workspace-switcher";
import { IconButton } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { HOME_PATH } from "@/lib/app-nav";
import { env } from "@/lib/env";
import { t } from "@/lib/i18n";

function Logo() {
  return (
    <Link
      href={HOME_PATH}
      aria-label={t("shell.homeLink")}
      className="flex items-center gap-2.5 self-start rounded-[8px] px-2.5 py-1 text-ink"
    >
      <TurnMark size={26} />
      <span className="font-display text-[20px] font-semibold tracking-[-0.02em]">
        {t("site.name")}
      </span>
    </Link>
  );
}

/** Logo, switcher, nav and user button: the persistent sidebar from `lg`, the drawer below it. */
function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <>
      <Logo />
      <WorkspaceSwitcher variant="sidebar" />
      <SidebarNav onNavigate={onNavigate} />
      <UserMenu variant="sidebar" />
    </>
  );
}

const SIDEBAR = "flex flex-col gap-5 bg-surface-raised px-3.5 pt-5 pb-3.5";

function MobileTopBar() {
  // Links inside the drawer close it (SidebarNav's onNavigate).
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-1 border-b border-line bg-surface-raised pr-2 pl-1 safe-top md:h-16 md:pr-4 md:pl-3 lg:hidden">
      <RadixDialog.Root open={drawerOpen} onOpenChange={setDrawerOpen}>
        <RadixDialog.Trigger asChild>
          <IconButton
            label={t("shell.openMenu")}
            icon={<ListIcon aria-hidden="true" className="size-6" />}
          />
        </RadixDialog.Trigger>
        <RadixDialog.Portal>
          <RadixDialog.Overlay className="fixed inset-0 z-40 bg-ink/45 data-[state=open]:animate-[fh-fade-in_200ms_ease-out]" />
          <RadixDialog.Content
            aria-describedby={undefined}
            // Focus the panel, not the close button (whose tooltip would open on focus).
            onOpenAutoFocus={(event) => {
              event.preventDefault();
              (event.currentTarget as HTMLElement).focus();
            }}
            className={`fixed inset-y-0 outline-none left-0 z-50 w-[min(304px,calc(100vw-48px))] border-r border-line pt-[max(20px,env(safe-area-inset-top))] pb-[max(14px,env(safe-area-inset-bottom))] shadow-raised data-[state=open]:animate-[fh-drawer-in_240ms_ease-out] ${SIDEBAR}`}
          >
            <RadixDialog.Title className="sr-only">{t("shell.menu")}</RadixDialog.Title>
            <RadixDialog.Close asChild>
              <IconButton
                label={t("shell.closeMenu")}
                icon={<XIcon aria-hidden="true" className="size-5" />}
                className="absolute top-3 right-2"
              />
            </RadixDialog.Close>
            <SidebarContent onNavigate={() => setDrawerOpen(false)} />
          </RadixDialog.Content>
        </RadixDialog.Portal>
      </RadixDialog.Root>
      <WorkspaceSwitcher variant="topbar" />
      <span className="flex-1" />
      <UserMenu variant="topbar" />
    </header>
  );
}

function ShellSkeleton() {
  return (
    <div aria-busy="true" className="min-h-dvh bg-surface lg:flex">
      <div className="flex h-14 items-center gap-3 border-b border-line bg-surface-raised px-4 md:h-16 lg:hidden">
        <Skeleton className="size-7 rounded-[8px]" />
        <Skeleton className="h-4 w-32" />
      </div>
      <div className={`hidden w-[264px] shrink-0 border-r border-line lg:flex lg:h-dvh ${SIDEBAR}`}>
        <Skeleton className="h-7 w-28" />
        <Skeleton className="h-[52px] rounded-[12px]" />
        {Array.from({ length: 6 }, (_, index) => (
          <Skeleton key={index} className="h-5 w-40" />
        ))}
      </div>
      <p role="status" className="sr-only">
        {t("app.loading")}
      </p>
    </div>
  );
}

/**
 * The TA app's persistent layout (DASH-001): sidebar from `lg`, top bar and drawer below it.
 * `workspaceId` is the `fh_ws` cookie read on the server. Without a valid one (no cookie, or the
 * user left that workspace) it hands over to /auth/continue, which picks the right workspace.
 */
export function AppShell({
  workspaceId,
  children,
}: {
  workspaceId: string | null;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const me = useQuery({
    queryKey: keys.me(),
    queryFn: async () => unwrap(await api.GET("/v1/me")),
  });
  const workspaces = useQuery({
    queryKey: keys.myWorkspaces(),
    queryFn: async () => unwrap(await api.GET("/v1/me/workspaces")),
  });

  const state = useMemo<ShellState | null>(() => {
    if (!me.data || !workspaces.data) return null;
    const rows = workspaces.data.map((row) => ({
      id: row.id,
      name: row.name,
      role: row.role,
      memberCount: row.member_count,
      slug: row.slug,
    }));
    const workspace = rows.find((row) => row.id === workspaceId);
    if (!workspace) return null;
    return {
      user: {
        id: me.data.id,
        name: me.data.full_name || me.data.email || "",
        email: me.data.email ?? "",
        avatarUrl: me.data.avatar_url,
      },
      workspace,
      workspaces: rows,
    };
  }, [me.data, workspaces.data, workspaceId]);

  const noWorkspace = !!workspaces.data && !!me.data && !state;
  useEffect(() => {
    if (!noWorkspace) return;
    const url = new URL("/auth/continue", env.siteUrl);
    url.searchParams.set("next", pathname);
    window.location.replace(url.toString());
  }, [noWorkspace, pathname]);

  if (me.isError || workspaces.isError) {
    return (
      <main className="page-gutter flex min-h-dvh items-center justify-center">
        <p role="alert" className="type-body max-w-sm text-center text-ink-muted">
          {t("app.loadFailed")}
        </p>
      </main>
    );
  }
  if (!state) return <ShellSkeleton />;

  return (
    <ShellContext.Provider value={state}>
      <a
        href="#main"
        className="sr-only z-50 rounded-sm bg-surface-raised px-3 py-2 focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        {t("shell.skipToContent")}
      </a>
      <div className="min-h-dvh bg-surface lg:flex">
        <aside
          className={`sticky top-0 hidden h-dvh w-[264px] shrink-0 border-r border-line lg:flex ${SIDEBAR}`}
        >
          <SidebarContent />
        </aside>
        <MobileTopBar />
        <main id="main" tabIndex={-1} className="min-w-0 flex-1 outline-none">
          {children}
        </main>
      </div>
    </ShellContext.Provider>
  );
}
