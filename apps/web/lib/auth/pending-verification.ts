// The email waiting to be verified (S-06). The address never goes in a URL (AGENTS.md hard
// rule 8), so the login form keeps it in this tab's sessionStorage for /verify-email.

const KEY = "fh_verify";

/** Seconds before another link may be sent: Supabase's `max_frequency` (FR-AUTH-02). */
export const RESEND_COOLDOWN_SECONDS = 60;

export interface PendingVerification {
  email: string;
  /** When the last link was sent, in ms since the epoch. */
  sentAt: number;
}

type Storage = Pick<globalThis.Storage, "getItem" | "setItem" | "removeItem">;

const NO_STORAGE: Storage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };

/** This tab's sessionStorage; reading `window.sessionStorage` itself throws when storage is blocked. */
export function tabStorage(): Storage {
  try {
    return window.sessionStorage;
  } catch {
    return NO_STORAGE;
  }
}

export function rememberPendingVerification(storage: Storage, value: PendingVerification): void {
  try {
    storage.setItem(KEY, JSON.stringify(value));
  } catch {
    // Storage can be off (private windows); /verify-email then sends the user back to sign in.
  }
}

/** The raw stored value, for `useSyncExternalStore` (a string is a stable snapshot). */
export function readPendingVerificationRaw(storage: Pick<Storage, "getItem">): string | null {
  try {
    return storage.getItem(KEY);
  } catch {
    return null;
  }
}

export function parsePendingVerification(raw: string | null): PendingVerification | null {
  try {
    const value = JSON.parse(raw ?? "null") as Partial<PendingVerification> | null;
    if (typeof value?.email === "string" && typeof value.sentAt === "number") {
      return { email: value.email, sentAt: value.sentAt };
    }
  } catch {
    // Unreadable: treat as nothing pending.
  }
  return null;
}

export function forgetPendingVerification(storage: Storage): void {
  try {
    storage.removeItem(KEY);
  } catch {
    // Nothing to clear.
  }
}

/** Whole seconds left before a resend is allowed, 0 when it is. */
export function cooldownLeft(sentAt: number, now: number): number {
  const left = RESEND_COOLDOWN_SECONDS - Math.floor((now - sentAt) / 1000);
  return Math.min(RESEND_COOLDOWN_SECONDS, Math.max(0, left));
}
