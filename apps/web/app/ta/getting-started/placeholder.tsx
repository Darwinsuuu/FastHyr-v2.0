"use client";

import { useQuery } from "@tanstack/react-query";

import { LogOutButton } from "@/components/auth/log-out-button";
import { api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { t } from "@/lib/i18n";
import { readWorkspaceId } from "@/lib/workspace";

export function GettingStartedPlaceholder() {
  const workspaces = useQuery({
    queryKey: keys.myWorkspaces(),
    queryFn: async () => unwrap(await api.GET("/v1/me/workspaces")),
  });
  const activeId = typeof document === "undefined" ? null : readWorkspaceId(document.cookie);
  const workspace = workspaces.data?.find((row) => row.id === activeId);

  return (
    <main className="page-gutter flex flex-col gap-6 py-8 md:py-12">
      <div className="flex flex-col gap-2">
        <h1 className="type-heading">
          {workspace
            ? t("workspaces.gettingStartedTitle", { name: workspace.name })
            : t("app.title")}
        </h1>
        <p className="type-body max-w-[640px] text-ink-muted">
          {t("workspaces.gettingStartedPlaceholder")}
        </p>
      </div>
      <LogOutButton className="self-start" />
    </main>
  );
}
