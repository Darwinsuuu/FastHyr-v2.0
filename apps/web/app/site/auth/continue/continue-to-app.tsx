"use client";

import { useEffect, useState } from "react";

import { Spinner } from "@/components/ui/spinner";
import { api, unwrap } from "@/lib/api/client";
import { chooseDestination } from "@/lib/auth/destination";
import { env } from "@/lib/env";
import { t } from "@/lib/i18n";
import { readWorkspaceId, workspaceCookie } from "@/lib/workspace";

export function ContinueToApp({ next }: { next: string | null }) {
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [me, workspaces] = await Promise.all([
        api.GET("/v1/me").then(unwrap),
        api.GET("/v1/me/workspaces").then(unwrap),
      ]);
      const destination = chooseDestination({
        next,
        lastWorkspaceId: me.last_workspace_id,
        cookieWorkspaceId: readWorkspaceId(document.cookie),
        workspaceIds: workspaces.map((workspace) => workspace.id),
      });
      if (cancelled) return;
      if (destination.workspaceId) {
        document.cookie = workspaceCookie(destination.workspaceId);
      }
      const base = destination.host === "app" ? env.appUrl : env.siteUrl;
      window.location.replace(new URL(destination.path, base).toString());
    })().catch(() => {
      if (!cancelled) setFailed(true);
    });
    return () => {
      cancelled = true;
    };
  }, [next]);

  return (
    <main className="page-gutter flex min-h-dvh items-center justify-center">
      {failed ? (
        <p role="alert" className="type-body max-w-sm text-center text-ink-muted">
          {t("auth.continueFailed")}
        </p>
      ) : (
        <p role="status" className="type-body flex items-center gap-3 text-ink-muted">
          <Spinner />
          {t("auth.continuing")}
        </p>
      )}
    </main>
  );
}
