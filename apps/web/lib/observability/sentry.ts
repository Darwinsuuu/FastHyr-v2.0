import type { ErrorEvent, EventHint } from "@sentry/nextjs";

import { env } from "@/lib/env";

import { scrubBreadcrumb, scrubEvent } from "./scrub";

// Sentry for the web (FND-009, DEPLOYMENT.md §5). Shared by the browser, Node and edge runtimes
// (instrumentation-client.ts and instrumentation.ts). An empty NEXT_PUBLIC_SENTRY_DSN turns it
// off. The release is the git SHA, injected at build time by withSentryConfig (next.config.ts).

export const sentryDsn = process.env.NEXT_PUBLIC_SENTRY_DSN ?? "";

type ApiErrorLike = { name?: unknown; status?: unknown; code?: unknown; requestId?: unknown };

/** Tags an event caused by an API error with the API's request ID, so it joins the API's event. */
export function tagApiError(event: ErrorEvent, hint: EventHint): ErrorEvent {
  const error = hint.originalException as ApiErrorLike | undefined;
  if (error && typeof error === "object" && error.name === "ApiError") {
    event.tags = {
      ...event.tags,
      ...(typeof error.requestId === "string" ? { request_id: error.requestId } : {}),
      ...(typeof error.status === "number" ? { api_status: String(error.status) } : {}),
      ...(typeof error.code === "string" ? { api_code: error.code } : {}),
    };
  }
  return event;
}

export function sentryOptions(runtime: "browser" | "nodejs" | "edge") {
  return {
    dsn: sentryDsn,
    enabled: sentryDsn !== "",
    environment: env.appEnv,
    initialScope: { tags: { component: "web", runtime } },
    // SDK v11 ignores sendDefaultPii and collects user info (and lets Sentry infer the browser's
    // IP address) unless dataCollection says otherwise.
    dataCollection: {
      userInfo: false,
      cookies: false,
      httpHeaders: false,
      httpBodies: [],
      urlQueryParams: false,
      stackFrameVariables: false,
    },
    debug: process.env.SENTRY_DEBUG === "1",
    tracesSampleRate: 0,
    beforeSend: (event: ErrorEvent, hint: EventHint) => scrubEvent(tagApiError(event, hint)),
    beforeBreadcrumb: scrubBreadcrumb,
  };
}
