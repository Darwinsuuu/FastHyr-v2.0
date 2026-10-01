"use client";

import * as Sentry from "@sentry/nextjs";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { sentryDsn } from "@/lib/observability/sentry";

import { throwServerTestError } from "./actions";

export function SentryCheck() {
  const [sent, setSent] = useState<string | null>(null);

  function sendClientError() {
    const eventId = Sentry.captureException(new Error("FastHyr Sentry test error (web browser)"));
    setSent(`Browser error sent (event ${eventId}).`);
  }

  async function sendServerError() {
    try {
      await throwServerTestError();
    } catch {
      setSent("Server error thrown. Look for it in the web project.");
    }
  }

  return (
    <main className="page-gutter flex max-w-[60ch] flex-col gap-4 py-10">
      <h1 className="type-heading">Sentry check</h1>
      <p className="text-ink-muted">
        {sentryDsn
          ? "Each button sends one test error to the web Sentry project."
          : "NEXT_PUBLIC_SENTRY_DSN is empty, so nothing is sent."}
      </p>
      <div className="flex flex-wrap gap-3">
        <Button onClick={sendClientError}>Send a browser error</Button>
        <Button variant="secondary" onClick={sendServerError}>
          Throw a server error
        </Button>
      </div>
      {sent && <p role="status">{sent}</p>}
    </main>
  );
}
