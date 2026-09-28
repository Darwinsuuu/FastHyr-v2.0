"use client";

import { useQuery } from "@tanstack/react-query";

import { LogOutButton } from "@/components/auth/log-out-button";
import { api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { plural, t } from "@/lib/i18n";

export function MePanel() {
  const me = useQuery({
    queryKey: keys.me(),
    queryFn: async () => unwrap(await api.GET("/v1/me")),
  });
  const workspaces = useQuery({
    queryKey: keys.myWorkspaces(),
    queryFn: async () => unwrap(await api.GET("/v1/me/workspaces")),
  });

  if (me.isPending || workspaces.isPending) {
    return <p className="type-body-sm mt-6 text-ink-muted">{t("app.loading")}</p>;
  }
  if (me.isError || workspaces.isError) {
    return (
      <p role="alert" className="type-body-sm mt-6 text-signal-gap">
        {t("app.loadFailed")}
      </p>
    );
  }

  return (
    <div className="mt-6 flex flex-col gap-6">
      <section className="rounded-md border border-line bg-surface-raised p-4 md:p-6">
        <p className="type-title break-words">
          {t("app.signedInAs", { name: me.data.full_name ?? me.data.email ?? "" })}
        </p>
        <p className="type-body-sm mt-1 text-ink-muted">
          {me.data.email_verified ? t("app.emailVerified") : t("app.emailNotVerified")}
        </p>
      </section>

      <section>
        <h2 className="type-label text-ink-muted">{t("app.workspacesHeading")}</h2>
        {workspaces.data.length === 0 ? (
          <p className="type-body-sm mt-3 text-ink-muted">{t("app.noWorkspaces")}</p>
        ) : (
          <ul className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {workspaces.data.map((workspace) => (
              <li
                key={workspace.id}
                className="rounded-md border border-line bg-surface-raised p-4"
              >
                <p className="type-title">{workspace.name}</p>
                <p className="type-body-sm mt-1 text-ink-muted">
                  {t(`app.role.${workspace.role}`)}
                  {workspace.is_owner ? ` · ${t("app.owner")}` : ""} ·{" "}
                  {plural("app.memberCount", workspace.member_count)}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <LogOutButton className="self-start" />
    </div>
  );
}
