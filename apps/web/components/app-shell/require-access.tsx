"use client";

import type { ReactNode } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { EmptyState } from "@/components/ui/empty-state";
import { t } from "@/lib/i18n";
import { type Action, can } from "@/lib/permissions";

/**
 * Shows a page only to roles allowed `action`; others (who don't see it in the nav but opened the
 * URL) get a plain no-access state. The API refuses the data anyway; this only avoids a broken page.
 */
export function RequireAccess({ action, children }: { action: Action; children: ReactNode }) {
  const { workspace } = useShell();
  if (!can(workspace.role, action)) {
    return (
      <div className="page-gutter py-10 md:py-16">
        <EmptyState title={t("shell.noAccessTitle")} description={t("shell.noAccessBody")} />
      </div>
    );
  }
  return children;
}
