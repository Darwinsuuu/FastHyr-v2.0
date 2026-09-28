import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

import { env } from "@/lib/env";
import { hostOf, internalPath, NEXT_PATH_HEADER, SIGN_IN_REQUIRED } from "@/lib/hosts";
import { supabaseCookieOptions } from "@/lib/supabase/cookies";

// Routes each request to its host's folder, refreshes the Supabase session cookie, and sends
// signed-out visitors on the app host to the site's login page.
export async function proxy(request: NextRequest) {
  const host = hostOf(request.headers.get("host"), env.appUrl);
  const { pathname, search } = request.nextUrl;
  const target = request.nextUrl.clone();
  target.pathname = internalPath(host, pathname);

  let response = NextResponse.rewrite(target, { request });
  const supabase = createServerClient(env.supabaseUrl, env.supabaseAnonKey, {
    cookieOptions: supabaseCookieOptions,
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (toSet, headers) => {
        toSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.rewrite(target, { request });
        toSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
        Object.entries(headers).forEach(([key, value]) => response.headers.set(key, value));
      },
    },
  });

  // getClaims() verifies the token against the project's signing keys and refreshes it if due.
  const { data } = await supabase.auth.getClaims();
  if (host === "app" && !data?.claims) {
    // Hand off to a route handler that redirects to the site's login page. A redirect returned
    // from here would be shortened to "/login" in dev, where both hosts share one origin, and
    // loop on the app host.
    const signIn = request.nextUrl.clone();
    signIn.pathname = SIGN_IN_REQUIRED;
    const headers = new Headers(request.headers);
    headers.set(NEXT_PATH_HEADER, `${pathname}${search}`);
    const handoff = NextResponse.rewrite(signIn, { request: { headers } });
    response.cookies.getAll().forEach((cookie) => handoff.cookies.set(cookie));
    return handoff;
  }
  return response;
}

export const config = {
  // Everything except Next.js internals and static files.
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
