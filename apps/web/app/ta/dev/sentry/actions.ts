"use server";

import { devToolsEnabled } from "@/lib/env";

// Throws on the server so onRequestError (instrumentation.ts) reports it.
export async function throwServerTestError(): Promise<void> {
  if (!devToolsEnabled) return;
  throw new Error("FastHyr Sentry test error (web server)");
}
