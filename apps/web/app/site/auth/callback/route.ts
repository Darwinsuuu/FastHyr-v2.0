import { NextResponse } from "next/server";

import { env } from "@/lib/env";
import { safeNextPath } from "@/lib/hosts";
import { supabaseServer } from "@/lib/supabase/server";

// Google and Microsoft sign-in (and email links) come back here with a one-time code.
export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const next = safeNextPath(url.searchParams.get("next"));

  if (code) {
    const supabase = await supabaseServer();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(new URL(next, env.appUrl));
    }
  }
  const login = new URL("/login", env.siteUrl);
  login.searchParams.set("error", "signin");
  return NextResponse.redirect(login);
}
