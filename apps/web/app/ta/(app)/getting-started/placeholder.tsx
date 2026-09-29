"use client";

import { useShell } from "@/components/app-shell/shell-context";
import { t } from "@/lib/i18n";

export function GettingStartedPlaceholder() {
  const { workspace } = useShell();
  return (
    <div className="page-gutter flex flex-col gap-2 py-6 md:py-10 lg:px-10 lg:py-9">
      <h1 className="type-heading">
        {t("workspaces.gettingStartedTitle", { name: workspace.name })}
      </h1>
      <p className="type-body max-w-[640px] text-ink-muted">
        {t("workspaces.gettingStartedPlaceholder")}
      </p>
    </div>
  );
}
