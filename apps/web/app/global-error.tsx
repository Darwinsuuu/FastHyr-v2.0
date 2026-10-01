"use client";

import "./globals.css";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

import { fontVariables } from "@/app/fonts";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { t } from "@/lib/i18n";

// The last-resort error page: an error no route caught. It replaces the root layout, so it brings
// its own <html> and <body>, and reports the error to Sentry (FND-009).
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="en" className={fontVariables}>
      <body className="bg-surface text-ink">
        <main className="flex min-h-dvh items-center justify-center px-4">
          <EmptyState
            title={t("error.title")}
            description={t("error.body")}
            action={<Button onClick={reset}>{t("error.retry")}</Button>}
          />
        </main>
      </body>
    </html>
  );
}
