import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { devToolsEnabled } from "@/lib/env";

import { InterviewPreview } from "./preview";

export const metadata: Metadata = {
  title: "Live interview preview · FastHyr",
  robots: { index: false },
};

// The live interview against the scripted stand-in for OpenAI and a fake API (INTV-005), for
// design checks and Playwright. Local and development only; QA and production get a 404.
// `?format=voice` for a voice-only interview, `?time=90` to start near the end.
export default async function InterviewPreviewPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  if (!devToolsEnabled) notFound();
  const query = await searchParams;
  const time = Number(query.time);
  return (
    <InterviewPreview
      video={query.format !== "voice"}
      timeLeftSeconds={Number.isFinite(time) && time > 0 ? Math.floor(time) : 30 * 60}
    />
  );
}
