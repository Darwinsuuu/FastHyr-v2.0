import { NextResponse } from "next/server";

import { applySignInProblemPath, isApplyPath } from "@/lib/apply/session";
import { continuePath, isOAuthProvider } from "@/lib/auth/flow";
import { env } from "@/lib/env";
import { isInterviewPath } from "@/lib/interview";
import { supabaseServer } from "@/lib/supabase/server";

// Google and Microsoft sign-in come back here with a one-time code, or with an error when the user
// cancelled. Links in Supabase's emails go to /auth/confirm instead (AUTH-002). Candidates signing
// in on an apply page or an interview link go straight back to it, in both cases (APPLY-002,
// INTV-002).
export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const next = url.searchParams.get("next");
  const provider = url.searchParams.get("provider");
  const candidatePage = isApplyPath(next) || isInterviewPath(next) ? next : null;

  if (code) {
    const supabase = await supabaseServer();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      // /auth/continue is the TA workspace routing; a candidate returns to the role they opened.
      const destination = candidatePage ?? continuePath(next);
      return NextResponse.redirect(new URL(destination, env.siteUrl));
    }
  }

  if (candidatePage) {
    const cancelled = url.searchParams.get("error") === "access_denied";
    return NextResponse.redirect(
      new URL(
        applySignInProblemPath(candidatePage, cancelled ? "cancelled" : "failed"),
        env.siteUrl,
      ),
    );
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
