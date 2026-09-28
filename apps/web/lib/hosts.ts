// One Next.js app serves two hosts (FRONTEND.md §1). proxy.ts rewrites every request into the
// folder for its host: app/site/* for the public site, app/ta/* for the TA app.

export type Host = "site" | "app";

/** Internal route that sends signed-out app visitors to the site's login page (proxy.ts). */
export const SIGN_IN_REQUIRED = "/ta/sign-in-required";

/** Carries the path a signed-out visitor wanted from proxy.ts to that route. */
export const NEXT_PATH_HEADER = "x-fh-next-path";

export const HOST_FOLDERS: Record<Host, string> = { site: "/site", app: "/ta" };

/** "app" for the TA app host (its hostname matches NEXT_PUBLIC_APP_URL), "site" otherwise. */
export function hostOf(requestHost: string | null, appUrl: string): Host {
  const hostname = (requestHost ?? "").split(":")[0]?.toLowerCase() ?? "";
  return hostname === new URL(appUrl).hostname.toLowerCase() ? "app" : "site";
}

/** The internal path a request is rewritten to, e.g. ("app", "/pipelines") → "/ta/pipelines". */
export function internalPath(host: Host, pathname: string): string {
  return pathname === "/" ? HOST_FOLDERS[host] : `${HOST_FOLDERS[host]}${pathname}`;
}

/** Where a signed-out visitor to the app host is sent: the site's login page, returning after. */
export function loginRedirect(siteUrl: string, pathname: string, search: string): URL {
  const url = new URL("/login", siteUrl);
  const next = `${pathname}${search}`;
  if (next !== "/") {
    url.searchParams.set("next", next);
  }
  return url;
}

/** A post-sign-in destination on the app host. Only same-host paths are allowed. */
export function safeNextPath(next: string | null): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.includes("\\")) {
    return "/";
  }
  return next;
}
