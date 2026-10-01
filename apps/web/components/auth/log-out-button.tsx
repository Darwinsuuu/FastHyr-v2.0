"use client";

import { SignOutIcon } from "@phosphor-icons/react";
import { useState } from "react";

import { Button, type ButtonProps } from "@/components/ui/button";
import { env } from "@/lib/env";
import { t } from "@/lib/i18n";
import { supabaseBrowser } from "@/lib/supabase/browser";
import { workspaceCookie } from "@/lib/workspace";

/**
 * Ends the session on this device only (FR-AUTH-09) and returns to the sign-in page, which sends
 * the next sign-in to `next` if given (the join page uses this to come back to the invite).
 */
export async function logOut(next?: string) {
  await supabaseBrowser().auth.signOut({ scope: "local" });
  // The next person on this device shouldn't open in this user's workspace.
  document.cookie = workspaceCookie(null);
  const login = new URL("/login", env.siteUrl);
  if (next) login.searchParams.set("next", next);
  window.location.assign(login.toString());
}

export function LogOutButton(props: Omit<ButtonProps, "onClick" | "loading">) {
  const [busy, setBusy] = useState(false);
  return (
    <Button
      variant="secondary"
      icon={<SignOutIcon aria-hidden="true" className="size-5" />}
      {...props}
      loading={busy}
      onClick={() => {
        setBusy(true);
        void logOut();
      }}
    >
      {t("auth.logOut")}
    </Button>
  );
}
