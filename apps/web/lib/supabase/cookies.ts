import type { CookieOptionsWithName } from "@supabase/ssr";

import { env } from "@/lib/env";

// Supabase session cookies (auth only). The browser client reads them to get the access token
// it sends to FastAPI, so they can't be httpOnly; they are Secure off localhost and SameSite=Lax.
export const supabaseCookieOptions: CookieOptionsWithName = {
  domain: env.cookieDomain,
  path: "/",
  sameSite: "lax",
  secure: env.siteUrl.startsWith("https://"),
};
