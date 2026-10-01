import { withSentryConfig } from "@sentry/nextjs/config";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Import only the icons we use from Phosphor's barrel file.
  experimental: { optimizePackageImports: ["@phosphor-icons/react"] },
};

// Sentry (FND-009). The release is the git SHA (Vercel's VERCEL_GIT_COMMIT_SHA, or SENTRY_RELEASE).
// Source maps upload only when SENTRY_AUTH_TOKEN, SENTRY_ORG and SENTRY_PROJECT are set (Vercel);
// local and CI builds skip it.
export default withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  authToken: process.env.SENTRY_AUTH_TOKEN,
  silent: !process.env.CI,
  sourcemaps: { disable: !process.env.SENTRY_AUTH_TOKEN },
  telemetry: false,
});
