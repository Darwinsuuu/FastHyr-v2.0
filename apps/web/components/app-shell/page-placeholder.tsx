"use client";

import type { ReactNode } from "react";

import { RequireAccess } from "@/components/app-shell/require-access";
import { EmptyState } from "@/components/ui/empty-state";
import { type MessageKey, t } from "@/lib/i18n";
import type { Action } from "@/lib/permissions";

/** A nav page that isn't built yet. The task that builds the page replaces its file. */
export function PagePlaceholder({
  title,
  action,
  children,
}: {
  title: MessageKey;
  action: Action;
  /** Anything already usable from this page, e.g. the New pipeline button. */
  children?: ReactNode;
}) {
  return (
    <RequireAccess action={action}>
      <div className="page-gutter flex flex-col gap-6 py-6 md:py-10 lg:px-10 lg:py-9">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <h1 className="type-heading">{t(title)}</h1>
          {children}
        </div>
        <div className="rounded-lg border border-line bg-surface-raised">
          <EmptyState title={t("shell.comingSoonTitle")} description={t("shell.comingSoonBody")} />
        </div>
      </div>
    </RequireAccess>
  );
}
