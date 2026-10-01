import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { devToolsEnabled } from "@/lib/env";

import { SentryCheck } from "./sentry-check";

export const metadata: Metadata = { title: "Sentry check · FastHyr", robots: { index: false } };

// Sends test errors to the web Sentry project (FND-009). Local and development only.
export default function SentryCheckPage() {
  if (!devToolsEnabled) notFound();
  return <SentryCheck />;
}
