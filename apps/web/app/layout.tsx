import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { siteName, tagline } from "@/lib/site";

export const metadata: Metadata = {
  title: siteName,
  description: tagline,
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
