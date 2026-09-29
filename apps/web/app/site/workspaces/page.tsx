import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AuthSplitLayout } from "@/components/auth/auth-split-layout";
import { LogOutButton } from "@/components/auth/log-out-button";
import { t } from "@/lib/i18n";
import { supabaseServer } from "@/lib/supabase/server";

export const metadata: Metadata = { title: t("auth.workspacesPageTitle") };

// Placeholder for Choose workspace, where signed-in users with no workspace land (FR-AUTH-04).
// AUTH-003 replaces it with the WorkspaceSelect frame (create or join a workspace).
export default async function WorkspacesPage() {
  const { data } = await (await supabaseServer()).auth.getClaims();
  if (!data?.claims) {
    redirect("/login");
  }
  const claims = data.claims as { email?: string; user_metadata?: { full_name?: string } };
  const name = claims.user_metadata?.full_name?.split(" ")[0] || claims.email || "";
  return (
    <AuthSplitLayout>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <h1 className="type-heading lg:text-[30px] lg:leading-9">
            {t("auth.workspacesTitle", { name })}
          </h1>
          <p className="text-[15px] leading-6 text-ink-muted">{t("auth.workspacesPlaceholder")}</p>
        </div>
        <LogOutButton className="self-start" />
      </div>
    </AuthSplitLayout>
  );
}
