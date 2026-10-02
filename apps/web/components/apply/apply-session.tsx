"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { ApplicationDialog } from "@/components/apply/application-dialog";
import { SentDialog } from "@/components/apply/sent-dialog";
import { SignInDialog } from "@/components/apply/sign-in-dialog";
import {
  type CandidateStatus,
  type MyApplication,
  type PublicPipeline,
  type SourceTag,
  applySource,
} from "@/lib/apply";
import {
  applyReturnPath,
  type Candidate,
  type ReturnState,
  type SignInIntent,
  type SignInProblem,
  withoutReturnParams,
} from "@/lib/apply/session";
import { type OAuthProvider, OAUTH_SCOPES } from "@/lib/auth/flow";
import { env } from "@/lib/env";
import type { Notice } from "@/lib/notices";
import { supabaseBrowser } from "@/lib/supabase/browser";
import { workspaceCookie } from "@/lib/workspace";

type Modal =
  | { kind: "signin"; intent: SignInIntent; problem: SignInProblem | null }
  | { kind: "form" }
  | { kind: "sent"; fullName: string }
  | null;

interface ApplySession {
  candidate: Candidate | null;
  /** When the signed-in candidate applied to this pipeline, or null (APPLY-003). */
  appliedAt: string | null;
  /** Where that application is, in candidate-safe words (APPLY-004). */
  status: CandidateStatus | null;
  /** Apply now: the form when signed in, else sign-in that opens the form afterwards. */
  startApply: () => void;
  /** The header's Sign in. */
  openSignIn: () => void;
  signOut: () => Promise<void>;
}

const ApplySessionContext = createContext<ApplySession | null>(null);

export function useApplySession(): ApplySession {
  const session = useContext(ApplySessionContext);
  if (!session) throw new Error("useApplySession needs an ApplySessionProvider");
  return session;
}

/**
 * Candidate sign-in on the apply page (APPLY-002): who is signed in, the sign-in and application
 * modals, and the Google or Microsoft round trip that comes back to this page (ADR-014).
 */
export function ApplySessionProvider({
  pipeline,
  source,
  initialCandidate,
  initialMine,
  notice,
  returning,
  children,
}: {
  pipeline: PublicPipeline;
  source: SourceTag;
  /** From the session claims, read on the server. */
  initialCandidate: Candidate | null;
  /** The candidate's application to this pipeline, read on the server. */
  initialMine: MyApplication | null;
  /** The current apply notice for the form's consent (COMP-002). */
  notice: Notice | null;
  /** The round trip's parameters, read on the server (`readReturn()`). */
  returning: ReturnState;
  children: ReactNode;
}) {
  const [candidate, setCandidate] = useState(initialCandidate);
  const router = useRouter();
  const [appliedAt, setAppliedAt] = useState(initialMine?.applied_at ?? null);
  const [status, setStatus] = useState(initialMine?.status ?? null);
  // A TA member of this workspace signed in with Google or Microsoft: allowed, warned (APPLY-004).
  const [workspaceMember, setWorkspaceMember] = useState(initialMine?.workspace_member ?? false);
  // Back from Google or Microsoft: open the form, or say why sign-in didn't finish.
  const [modal, setModal] = useState<Modal>(() => {
    if (returning.openForm && pipeline.availability === "accepting" && !initialMine?.applied_at) {
      return { kind: "form" };
    }
    if (returning.problem) {
      return { kind: "signin", intent: returning.intent, problem: returning.problem };
    }
    return null;
  });

  // After `router.refresh()` the server has read the application again; take its answer.
  const [readMine, setReadMine] = useState(initialMine);
  if (initialMine !== readMine) {
    setReadMine(initialMine);
    if (initialMine) {
      setAppliedAt(initialMine.applied_at ?? null);
      setStatus(initialMine.status ?? null);
      setWorkspaceMember(initialMine.workspace_member);
    }
  }

  // A reload or a shared link shouldn't reopen the form or repeat the error.
  useEffect(() => {
    if (!returning.clean) return;
    const search = new URLSearchParams(window.location.search);
    window.history.replaceState(
      window.history.state,
      "",
      withoutReturnParams(window.location.pathname, search),
    );
  }, [returning.clean]);

  const startApply = useCallback(() => {
    setModal(candidate ? { kind: "form" } : { kind: "signin", intent: "apply", problem: null });
  }, [candidate]);

  // The tag to record: the one in the link, else the one kept for this pipeline.
  const currentSource = useCallback(
    () =>
      source !== "direct"
        ? source
        : applySource(window.sessionStorage, pipeline.workspace_slug, pipeline.slug),
    [source, pipeline.workspace_slug, pipeline.slug],
  );

  const openSignIn = useCallback(() => {
    setModal({ kind: "signin", intent: "browse", problem: null });
  }, []);

  const signOut = useCallback(async () => {
    // This device only, as Log out does for TA users (FR-AUTH-09); the candidate stays on the page.
    await supabaseBrowser().auth.signOut({ scope: "local" });
    document.cookie = workspaceCookie(null);
    setCandidate(null);
    setAppliedAt(null);
    setStatus(null);
    setWorkspaceMember(false);
  }, []);

  const signInWith = useCallback(
    async (provider: OAuthProvider, intent: SignInIntent): Promise<boolean> => {
      // The stored tag wins: the address bar may have lost it on an earlier round trip.
      const tag = currentSource();
      const callback = new URL("/auth/callback", env.siteUrl);
      callback.searchParams.set(
        "next",
        applyReturnPath(pipeline.workspace_slug, pipeline.slug, { intent, source: tag }),
      );
      callback.searchParams.set("provider", provider);
      const { error } = await supabaseBrowser().auth.signInWithOAuth({
        provider,
        options: { redirectTo: callback.toString(), scopes: OAUTH_SCOPES[provider] },
      });
      // On success the browser is already leaving for the provider.
      return !error;
    },
    [pipeline.workspace_slug, pipeline.slug, currentSource],
  );

  const session = useMemo(
    () => ({ candidate, appliedAt, status, startApply, openSignIn, signOut }),
    [candidate, appliedAt, status, startApply, openSignIn, signOut],
  );

  return (
    <ApplySessionContext.Provider value={session}>
      {children}
      <SignInDialog
        open={modal?.kind === "signin"}
        onOpenChange={(open) => !open && setModal(null)}
        pipeline={pipeline}
        intent={modal?.kind === "signin" ? modal.intent : "browse"}
        problem={modal?.kind === "signin" ? modal.problem : null}
        onSignIn={signInWith}
      />
      {candidate && !appliedAt && (
        <ApplicationDialog
          // A different account starts a fresh form.
          key={candidate.id}
          open={modal?.kind === "form"}
          onOpenChange={(open) => !open && setModal(null)}
          pipeline={pipeline}
          candidate={candidate}
          notice={notice}
          workspaceMember={workspaceMember}
          source={currentSource}
          // The role stopped taking applications while the form was open: the page catches up.
          onNotAccepting={() => router.refresh()}
          onNotYou={async () => {
            await signOut();
            setModal({ kind: "signin", intent: "apply", problem: null });
          }}
          onApplied={(application, fullName) => {
            setAppliedAt(application.applied_at);
            // Applied before (another tab): the page reads the real status again.
            if (application.created) setStatus("received");
            else router.refresh();
            // Applied before (another tab): no "sent", the page shows the application instead.
            setModal(application.created ? { kind: "sent", fullName } : null);
          }}
        />
      )}
      {candidate && (
        <SentDialog
          open={modal?.kind === "sent"}
          onOpenChange={(open) => !open && setModal(null)}
          pipeline={pipeline}
          fullName={modal?.kind === "sent" ? modal.fullName : ""}
          email={candidate.email}
        />
      )}
    </ApplySessionContext.Provider>
  );
}
