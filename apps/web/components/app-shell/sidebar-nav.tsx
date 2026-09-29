"use client";

import {
  BuildingsIcon,
  CoinsIcon,
  EnvelopeSimpleIcon,
  FunnelSimpleIcon,
  type Icon,
  ReceiptIcon,
  RocketLaunchIcon,
  SquaresFourIcon,
  StackIcon,
  UsersFourIcon,
  UsersThreeIcon,
} from "@phosphor-icons/react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useShell } from "@/components/app-shell/shell-context";
import { type NavIcon, navFor, navItemFor } from "@/lib/app-nav";
import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";

const ICONS: Record<NavIcon, Icon> = {
  gettingStarted: RocketLaunchIcon,
  overview: SquaresFourIcon,
  pipelines: FunnelSimpleIcon,
  candidates: UsersThreeIcon,
  billing: ReceiptIcon,
  creditUsage: CoinsIcon,
  company: BuildingsIcon,
  departments: StackIcon,
  members: UsersFourIcon,
  emailTemplates: EnvelopeSimpleIcon,
};

/** The sidebar's links for the active role; `onNavigate` closes the phone drawer. */
export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const { workspace } = useShell();
  const pathname = usePathname();
  const current = navItemFor(pathname)?.href;

  return (
    <nav
      aria-label={t("shell.mainNav")}
      className="-mr-1.5 ml-2 flex min-h-0 flex-1 flex-col gap-7 overflow-y-auto pr-1.5"
    >
      {navFor(workspace.role).map((section) => (
        <div key={section.heading ?? "main"} className="flex flex-col gap-0.5">
          {section.heading && (
            <h2 className="px-2.5 pb-1.5 text-[11px] font-[650] tracking-[0.08em] text-ink-muted uppercase">
              {t(section.heading)}
            </h2>
          )}
          <ul className="flex flex-col gap-0.5">
            {section.items.map((item) => {
              const ItemIcon = ICONS[item.icon];
              const active = item.href === current;
              return (
                <li key={item.href} className={section.heading ? "ml-3" : undefined}>
                  <Link
                    href={item.href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex h-11 items-center gap-2.5 rounded-[8px] px-2.5 text-[15px] transition-colors duration-200 ease-out lg:h-9 lg:text-[14px]",
                      active
                        ? "bg-evergreen-soft font-[650] text-evergreen"
                        : "font-medium text-ink hover:bg-surface-sunk",
                    )}
                  >
                    <ItemIcon
                      aria-hidden="true"
                      weight={active ? "bold" : "regular"}
                      className={cn("size-[18px] shrink-0", !active && "text-ink-muted")}
                    />
                    {t(item.label)}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
