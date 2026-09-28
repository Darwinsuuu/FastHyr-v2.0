"use client";

import { SignOutIcon } from "@phosphor-icons/react";
import { useState } from "react";

import { Button, type ButtonProps } from "@/components/ui/button";
import { env } from "@/lib/env";
import { t } from "@/lib/i18n";
import { supabaseBrowser } from "@/lib/supabase/browser";
import { workspaceCookie } from "@/lib/workspace";

/** Ends the session on this device only (FR-AUTH-09) and returns to the sign-in page. */
export async function logOut() {
  await supabaseBrowser().auth.signOut({ scope: "local" });
  // The next person on this device shouldn't open in this user's workspace.
  document.cookie = workspaceCookie(null);
  window.location.assign(new URL("/login", env.siteUrl).toString());
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
