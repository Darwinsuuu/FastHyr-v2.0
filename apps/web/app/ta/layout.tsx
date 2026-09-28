import type { ReactNode } from "react";

import { ApiProvider } from "@/lib/api/provider";

// The TA app host. proxy.ts has already sent signed-out visitors to the login page.
// The AppShell (sidebar, workspace switcher) arrives in DASH-001.
export default function TaLayout({ children }: { children: ReactNode }) {
  return <ApiProvider>{children}</ApiProvider>;
}
