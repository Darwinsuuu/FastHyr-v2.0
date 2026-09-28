import { headers } from "next/headers";
import { NextResponse } from "next/server";

import { env } from "@/lib/env";
import { loginRedirect, NEXT_PATH_HEADER, safeNextPath } from "@/lib/hosts";

// proxy.ts rewrites signed-out requests on the app host here; this sends them to the site's
// login page with the path they wanted, so they return to it after signing in.
export async function GET() {
  const next = safeNextPath((await headers()).get(NEXT_PATH_HEADER));
  const [pathname = "/", query = ""] = next.split("?");
  return NextResponse.redirect(loginRedirect(env.siteUrl, pathname, query ? `?${query}` : ""));
}
