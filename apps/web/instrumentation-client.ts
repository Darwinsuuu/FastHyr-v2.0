import * as Sentry from "@sentry/nextjs";

import { sentryOptions } from "@/lib/observability/sentry";

// Browser errors to the web Sentry project (FND-009). Session replay stays off: it would record
// what people type and see.
Sentry.init(sentryOptions("browser"));

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
