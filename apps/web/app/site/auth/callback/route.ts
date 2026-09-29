import { NextResponse } from "next/server";

import { continuePath, isOAuthProvider } from "@/lib/auth/flow";
import { env } from "@/lib/env";
import { supabaseServer } from "@/lib/supabase/server";

// Google and Microsoft sign-in come back here with a one-time code, or with an error when the user
// cancelled. Links in Supabase's emails go to /auth/confirm instead (AUTH-002).
export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const next = url.searchParams.get("next");
  const provider = url.searchParams.get("provider");

  if (code) {
    const supabase = await supabaseServer();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(new URL(continuePath(next), env.siteUrl));
    }
  }

  const login = new URL("/login", env.siteUrl);
  if (next) login.searchParams.set("next", next);
  const errorCode = url.searchParams.get("error_code");
  if (errorCode === "otp_expired") {
    login.searchParams.set("error", "link-expired");
  } else if (url.searchParams.get("error") === "access_denied" && isOAuthProvider(provider)) {
    // The user cancelled or declined at Google or Microsoft.
    login.searchParams.set("error", "cancelled");
    login.searchParams.set("provider", provider);
  } else {
    login.searchParams.set("error", "signin");
  }
  return NextResponse.redirect(login);
}
