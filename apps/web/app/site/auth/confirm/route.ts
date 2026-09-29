import { NextResponse } from "next/server";

import { continuePath } from "@/lib/auth/flow";
import { confirmDestination, isEmailLinkType } from "@/lib/auth/links";
import { env } from "@/lib/env";
import { supabaseServer } from "@/lib/supabase/server";

// Links in Supabase's verification and password-reset emails (supabase/templates) land here with
// a single-use token hash. Verifying it on the server signs the user in, in any browser.
export async function GET(request: Request) {
  const url = new URL(request.url);
  const type = url.searchParams.get("type");
  const tokenHash = url.searchParams.get("token_hash");
  const next = url.searchParams.get("next") || null;

  let verified = false;
  if (tokenHash && isEmailLinkType(type)) {
    const supabase = await supabaseServer();
    const { error } = await supabase.auth.verifyOtp({ type, token_hash: tokenHash });
    verified = !error;
  }
  return NextResponse.redirect(
    new URL(confirmDestination({ type, verified, continueTo: continuePath(next) }), env.siteUrl),
  );
}
