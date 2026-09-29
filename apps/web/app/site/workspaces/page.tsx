import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { ChooseWorkspace } from "@/app/site/workspaces/choose-workspace";
import { ApiProvider } from "@/lib/api/provider";
import { t } from "@/lib/i18n";
import { supabaseServer } from "@/lib/supabase/server";

export const metadata: Metadata = { title: t("workspaces.pageTitle") };

type Claims = {
  sub: string;
  email?: string;
  user_metadata?: {
    full_name?: string;
    name?: string;
    avatar_url?: string;
    picture?: string;
    email_verified?: boolean;
  };
};

// Choose workspace (frame WorkspaceSelect, FR-AUTH-04 to FR-AUTH-06): create a workspace or
// join one with an invite. People who already have workspaces can open one from here too.
export default async function WorkspacesPage() {
  const { data } = await (await supabaseServer()).auth.getClaims();
  if (!data?.claims) {
    // Plain /login: `next` is always an app-host path, and this page is on the site host.
    redirect("/login");
  }
  const claims = data.claims as unknown as Claims;
  // Unverified email + password accounts can't create or join a workspace (FR-AUTH-03).
  if (claims.user_metadata?.email_verified === false) {
    redirect("/verify-email");
  }
  const fullName = claims.user_metadata?.full_name || claims.user_metadata?.name || "";
  return (
    <ApiProvider>
      <ChooseWorkspace
        user={{
          id: claims.sub,
          email: claims.email ?? "",
          fullName,
          avatarUrl: claims.user_metadata?.avatar_url || claims.user_metadata?.picture || null,
        }}
      />
    </ApiProvider>
  );
}
