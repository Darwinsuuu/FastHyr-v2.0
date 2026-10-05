"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState, useTransition } from "react";

import { DeviceCheck, type DeviceCheckNotices } from "@/components/interview/device-check";
import { InterviewHeader } from "@/components/interview/interview-header";
import { InterviewLinkCard } from "@/components/interview/interview-link-card";
import { LiveInterview } from "@/components/interview/live-interview";
import type { InterviewDevices } from "@/components/interview/use-interview-session";
import type { SignInProblem } from "@/lib/apply/session";
import { type InterviewLink, isOpenState } from "@/lib/interview";
import { apiInterviewClient } from "@/lib/interview/client";

type Step = { name: "card" } | { name: "check" } | { name: "live"; devices: InterviewDevices };

/**
 * The link page's steps: the S-01 card for the link's state, the device check (INTV-003), then
 * the live interview (INTV-005). When the interview ends, the page reloads the link and shows
 * its new state (finished, or resume after a drop).
 */
export function InterviewFlow({
  token,
  link,
  notices,
  signedInEmail,
  signInProblem,
  allowFake,
}: {
  token: string;
  link: InterviewLink;
  notices: DeviceCheckNotices | null;
  signedInEmail: string | null;
  signInProblem: SignInProblem | null;
  allowFake: boolean;
}) {
  const router = useRouter();
  const [step, setStep] = useState<Step>({ name: "card" });
  const [, startTransition] = useTransition();
  const client = useMemo(() => apiInterviewClient(token), [token]);

  // Ending keeps the finishing screen up until the refreshed link arrives with the card.
  const ended = () =>
    startTransition(() => {
      router.refresh();
      setStep({ name: "card" });
    });

  if (step.name === "live") {
    return (
      <LiveInterview
        company={link.company}
        jobTitle={link.job_title}
        video={link.format === "video_voice"}
        devices={step.devices}
        client={client}
        allowFake={allowFake}
        onEnded={ended}
      />
    );
  }

  // A link that closed meanwhile (the page refreshed) shows its new state instead.
  const checking = step.name === "check" && isOpenState(link.state);
  return (
    <div className="flex min-h-dvh flex-col bg-surface">
      <InterviewHeader company={link.company} />
      <main className="page-gutter flex flex-1 flex-col items-center pt-6 pb-12 md:pt-12 lg:justify-center lg:pt-12 lg:pb-18">
        {checking ? (
          <DeviceCheck
            token={token}
            link={link}
            notices={notices}
            onBack={() => setStep({ name: "card" })}
            onStarted={(devices) => setStep({ name: "live", devices })}
          />
        ) : (
          <InterviewLinkCard
            token={token}
            link={link}
            signedInEmail={signedInEmail}
            signInProblem={signInProblem}
            onStart={() => setStep({ name: "check" })}
          />
        )}
      </main>
    </div>
  );
}
