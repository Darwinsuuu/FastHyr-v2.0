import * as Sentry from "@sentry/nextjs";

import { sentryOptions } from "@/lib/observability/sentry";

// Server and edge errors to the web Sentry project (FND-009).
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") Sentry.init(sentryOptions("nodejs"));
  if (process.env.NEXT_RUNTIME === "edge") Sentry.init(sentryOptions("edge"));
}

// Errors thrown while rendering server components, route handlers and server actions.
export const onRequestError = Sentry.captureRequestError;
