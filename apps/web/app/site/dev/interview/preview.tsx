"use client";

import { useMemo, useState } from "react";

import { LiveInterview } from "@/components/interview/live-interview";
import { Button } from "@/components/ui/button";
import type { InterviewClient } from "@/lib/interview/client";

const TOPICS = ["Warm-up", "Platform migration", "Working with other teams", "Your questions"];

/** A fake API: a fixed session, heartbeats that count down, and an end that always works. */
function previewClient(timeLeftSeconds: number): InterviewClient {
  let startedAt = 0;
  const left = () => Math.max(0, timeLeftSeconds - Math.floor((Date.now() - startedAt) / 1000));
  return {
    async open() {
      startedAt = Date.now();
      return {
        // The API's AI_FAKE answer, which plays the scripted conversation.
        sdp: "v=0\r\ns=fake\r\n",
        heartbeatSeconds: 15,
        session: {
          attemptId: "00000000-0000-4000-8000-000000000001",
          timeLeftSeconds,
          topics: TOPICS.map((title, index) => ({ number: index + 1, title })),
          topicNumber: 1,
        },
      };
    },
    async heartbeat() {
      const seconds = left();
      return { status: seconds === 0 ? "ended" : "active", timeLeftSeconds: seconds };
    },
    async complete() {
      await new Promise((resolve) => setTimeout(resolve, 400));
    },
  };
}

export function InterviewPreview({
  video,
  timeLeftSeconds,
}: {
  video: boolean;
  timeLeftSeconds: number;
}) {
  const [run, setRun] = useState(1);
  const [ended, setEnded] = useState(false);
  const client = useMemo(() => previewClient(timeLeftSeconds), [timeLeftSeconds]);

  if (ended) {
    return (
      <main className="page-gutter flex min-h-dvh flex-col items-center justify-center gap-4 bg-surface">
        <h1 className="type-heading">Session ended</h1>
        <p className="type-body text-ink-muted">
          The link page would now show the link&apos;s state.
        </p>
        <Button
          side="candidate"
          onClick={() => {
            setEnded(false);
            setRun((count) => count + 1);
          }}
        >
          Start again
        </Button>
      </main>
    );
  }

  return (
    <LiveInterview
      key={run}
      company={{ name: "Acme Talent", logo_url: null, website: null, careers_url: null }}
      jobTitle="Senior Backend Engineer"
      video={video}
      devices={{ camera: null, microphone: null }}
      client={client}
      allowFake
      onEnded={() => setEnded(true)}
    />
  );
}
