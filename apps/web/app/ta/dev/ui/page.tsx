import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { devToolsEnabled } from "@/lib/env";

import { Gallery } from "./gallery";

export const metadata: Metadata = { title: "UI kit · FastHyr", robots: { index: false } };

// The component gallery (FND-012). Local and development only; QA and production get a 404.
export default function UiGalleryPage() {
  if (!devToolsEnabled) notFound();
  return <Gallery />;
}
