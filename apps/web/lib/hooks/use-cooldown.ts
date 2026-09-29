"use client";

import { useEffect, useState } from "react";

import { cooldownLeft } from "@/lib/auth/pending-verification";

/** Seconds left of the resend cooldown that started at `sentAt` (ms), ticking once a second. */
export function useCooldown(sentAt: number | null): number {
  const [now, setNow] = useState(() => Date.now());
  // A sentAt newer than `now` counts as a full cooldown until the next tick.
  const left = sentAt === null ? 0 : cooldownLeft(sentAt, now);
  const running = left > 0;

  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [running]);

  return left;
}
