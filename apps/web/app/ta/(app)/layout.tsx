import { headers } from "next/headers";
import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell/app-shell";
import { readWorkspaceId } from "@/lib/workspace";

// Every TA app page sits in the app shell (DASH-001). The active workspace comes from the
// `fh_ws` cookie; the shell checks it against the user's workspaces.
export default async function AppShellLayout({ children }: { children: ReactNode }) {
  const workspaceId = readWorkspaceId((await headers()).get("cookie") ?? "");
  return <AppShell workspaceId={workspaceId}>{children}</AppShell>;
}
