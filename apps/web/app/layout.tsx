import "./globals.css";

import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { fontVariables } from "@/app/fonts";
import { t } from "@/lib/i18n";

export const metadata: Metadata = {
  title: t("site.name"),
  description: t("site.tagline"),
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F7F2EA" },
    { media: "(prefers-color-scheme: dark)", color: "#141C1A" },
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={fontVariables}>
      <body className="bg-surface text-ink">{children}</body>
    </html>
  );
}
