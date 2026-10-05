"use client";

import {
  ArrowUpRightIcon,
  BrowserIcon,
  CheckCircleIcon,
  ClockCountdownIcon,
  ClockIcon,
  LockSimpleIcon,
  MicrophoneIcon,
  SunIcon,
  UserSwitchIcon,
  VideoCameraIcon,
  WarningCircleIcon,
  WifiSlashIcon,
} from "@phosphor-icons/react";
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { GoogleMark, MicrosoftMark } from "@/components/auth/provider-marks";
import { Button } from "@/components/ui/button";
import type { SignInProblem } from "@/lib/apply/session";
import { type OAuthProvider, OAUTH_SCOPES } from "@/lib/auth/flow";
import { env } from "@/lib/env";
import { plural, t } from "@/lib/i18n";
import {
  accommodationHref,
  type InterviewLink,
  interviewPath,
  SIGNIN_PARAM,
} from "@/lib/interview";
import { noticeLinkHref } from "@/lib/notices";
import { supabaseBrowser } from "@/lib/supabase/browser";
import { workspaceCookie } from "@/lib/workspace";

const linkClass = "text-evergreen underline hover:text-persimmon";

/**
 * The S-01 card for the link's state. "Check my camera and mic", "Continue my interview" and
 * "Try again" call `onStart`, which opens the device check (INTV-003).
 */
export function InterviewLinkCard({
  token,
  link,
  signedInEmail,
  signInProblem,
  onStart,
}: {
  token: string;
  link: InterviewLink;
  signedInEmail: string | null;
  signInProblem: SignInProblem | null;
  onStart: () => void;
}) {
  // A reload or a shared link shouldn't repeat the sign-in error.
  useEffect(() => {
    const url = new URL(window.location.href);
    if (!url.searchParams.has(SIGNIN_PARAM)) return;
    url.searchParams.delete(SIGNIN_PARAM);
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}`);
  }, []);

  return (
    <section className="flex w-full max-w-[640px] flex-col gap-6 rounded-lg border border-line bg-surface-raised p-6 shadow-raised md:p-10">
      <LinkState
        token={token}
        link={link}
        signedInEmail={signedInEmail}
        signInProblem={signInProblem}
        onStart={onStart}
      />
    </section>
  );
}

function LinkState({
  token,
  link,
  signedInEmail,
  signInProblem,
  onStart,
}: {
  token: string;
  link: InterviewLink;
  signedInEmail: string | null;
  signInProblem: SignInProblem | null;
  onStart: () => void;
}) {
  const company = link.company.name;
  const name = link.first_name ?? "";
  switch (link.state) {
    case "welcome":
      return <Welcome link={link} onStart={onStart} />;
    case "resume":
      return (
        <Message
          title={name ? t("interview.resume.title", { name }) : t("interview.resume.titleNoName")}
          meta={<RoleLine link={link} />}
          action={
            <Button side="candidate" size="lg" onClick={onStart} className="w-full sm:w-auto">
              {t("interview.resume.continue")}
            </Button>
          }
        >
          <p>
            {t("interview.resume.body")}{" "}
            {plural("interview.resume.minutesLeft", link.minutes_left ?? 1)}
          </p>
        </Message>
      );
    case "sign_in":
      return <SignIn token={token} link={link} problem={signInProblem} />;
    case "wrong_account":
      return <WrongAccount email={signedInEmail} />;
    case "expired":
      return (
        <Message
          icon={<ClockCountdownIcon />}
          title={t("interview.expired.title")}
          action={
            link.company.website ? (
              <a
                href={link.company.website}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-[15px] font-semibold text-persimmon-ink underline hover:text-evergreen"
              >
                {t("interview.expired.website", { company })}
                <ArrowUpRightIcon aria-hidden="true" className="size-4" />
                <span className="sr-only"> {t("interview.newTab")}</span>
              </a>
            ) : undefined
          }
        >
          <p>{t("interview.expired.body", { expiry: link.expires_label, company })}</p>
        </Message>
      );
    case "completed":
      return (
        <Message icon={<CheckCircleIcon />} title={t("interview.completed.title")}>
          <p>
            {name
              ? t("interview.completed.body", { name, company })
              : t("interview.completed.bodyNoName", { company })}
          </p>
        </Message>
      );
    case "unavailable":
      return (
        <Message icon={<LockSimpleIcon />} title={t("interview.unavailable.title")}>
          <p>{t("interview.unavailable.body", { company })}</p>
        </Message>
      );
    case "technical_problem":
      return (
        <Message
          icon={<WifiSlashIcon />}
          title={t("interview.technical.title")}
          action={
            <Button side="candidate" size="lg" onClick={onStart} className="w-full sm:w-auto">
              {t("interview.technical.retry")}
            </Button>
          }
        >
          <p>{t("interview.technical.body", { expiry: link.expires_label })}</p>
        </Message>
      );
  }
}

function Welcome({ link, onStart }: { link: InterviewLink; onStart: () => void }) {
  const company = link.company.name;
  const accommodation = accommodationHref(link.company);
  const video = link.format === "video_voice";
  const bullets: { icon: ReactNode; text: string }[] = [
    { icon: <SunIcon />, text: t("interview.welcome.quiet") },
    { icon: <BrowserIcon />, text: t("interview.welcome.browser") },
    video
      ? { icon: <VideoCameraIcon />, text: t("interview.welcome.video") }
      : { icon: <MicrophoneIcon />, text: t("interview.welcome.voice") },
    { icon: <ClockIcon />, text: t("interview.welcome.openUntil", { expiry: link.expires_label }) },
  ];
  return (
    <>
      <div className="flex flex-col gap-3">
        <h1 className="type-display-lg break-words">
          {link.first_name
            ? t("interview.welcome.title", { name: link.first_name })
            : t("interview.welcome.titleNoName")}
        </h1>
        <RoleLine link={link} />
      </div>
      <p className="type-body">{t("interview.welcome.body", { title: link.job_title })}</p>
      <div className="flex flex-col gap-3 rounded-md bg-surface px-4 py-4 md:px-5">
        <h2 className="text-[12px] leading-4 font-semibold tracking-[0.08em] text-ink-muted uppercase">
          {t("interview.welcome.beforeYouStart")}
        </h2>
        <ul className="flex flex-col gap-2.5">
          {bullets.map((bullet) => (
            <li key={bullet.text} className="flex gap-3 text-[15px] leading-[22px]">
              <span aria-hidden="true" className="mt-px shrink-0 text-evergreen [&_svg]:size-5">
                {bullet.icon}
              </span>
              {bullet.text}
            </li>
          ))}
        </ul>
      </div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Button side="candidate" size="lg" onClick={onStart} className="w-full sm:w-auto">
          {t("interview.welcome.start")}
        </Button>
        {accommodation && (
          <a
            href={accommodation}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex min-h-11 items-center justify-center rounded-md px-3 text-[15px] font-semibold text-persimmon-ink hover:bg-persimmon-soft"
          >
            {t("interview.welcome.accommodation")}
            <span className="sr-only"> {t("interview.newTab")}</span>
          </a>
        )}
      </div>
      <p className="border-t border-line pt-4 text-[13px] leading-5 text-ink-muted">
        {t("interview.welcome.decision", { company })}{" "}
        <a
          href={noticeLinkHref("ai_in_hiring")}
          target="_blank"
          rel="noopener noreferrer"
          className={linkClass}
        >
          {t("interview.welcome.howAi")}
          <span className="sr-only"> {t("interview.newTab")}</span>
        </a>
      </p>
    </>
  );
}

function SignIn({
  token,
  link,
  problem,
}: {
  token: string;
  link: InterviewLink;
  problem: SignInProblem | null;
}) {
  const [busy, setBusy] = useState<OAuthProvider | null>(null);
  const [failed, setFailed] = useState(false);

  async function signIn(provider: OAuthProvider) {
    setBusy(provider);
    setFailed(false);
    const callback = new URL("/auth/callback", env.siteUrl);
    callback.searchParams.set("next", interviewPath(token));
    callback.searchParams.set("provider", provider);
    const { error } = await supabaseBrowser().auth.signInWithOAuth({
      provider,
      options: { redirectTo: callback.toString(), scopes: OAUTH_SCOPES[provider] },
    });
    // On success the browser is already leaving for the provider.
    if (error) {
      setBusy(null);
      setFailed(true);
    }
  }

  const alert = failed
    ? t("interview.signIn.failed")
    : problem
      ? t(`interview.signIn.${problem}`)
      : null;

  return (
    <Message
      title={t("interview.signIn.title")}
      meta={<RoleLine link={link} />}
      action={
        <div className="flex w-full flex-col gap-2.5">
          <Button
            variant="secondary"
            side="candidate"
            size="lg"
            icon={<GoogleMark />}
            loading={busy === "google"}
            disabled={busy !== null && busy !== "google"}
            onClick={() => void signIn("google")}
          >
            {t("interview.signIn.google")}
          </Button>
          <Button
            variant="secondary"
            side="candidate"
            size="lg"
            icon={<MicrosoftMark />}
            loading={busy === "azure"}
            disabled={busy !== null && busy !== "azure"}
            onClick={() => void signIn("azure")}
          >
            {t("interview.signIn.microsoft")}
          </Button>
        </div>
      }
    >
      {alert && <Alert>{alert}</Alert>}
      <p>{t("interview.signIn.body", { email: link.masked_email ?? "" })}</p>
    </Message>
  );
}

function WrongAccount({ email }: { email: string | null }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  async function switchAccount() {
    setBusy(true);
    setFailed(false);
    // This device only, as on the apply page; the page then asks for the right account.
    const { error } = await supabaseBrowser().auth.signOut({ scope: "local" });
    if (error) {
      setBusy(false);
      setFailed(true);
      return;
    }
    document.cookie = workspaceCookie(null);
    router.refresh();
  }

  return (
    <Message
      icon={<UserSwitchIcon />}
      title={t("interview.wrongAccount.title")}
      action={
        <Button
          side="candidate"
          size="lg"
          loading={busy}
          onClick={() => void switchAccount()}
          className="w-full sm:w-auto"
        >
          {t("interview.wrongAccount.switch")}
        </Button>
      }
    >
      {failed && <Alert>{t("interview.wrongAccount.failed")}</Alert>}
      <p>
        {email
          ? t("interview.wrongAccount.body", { email })
          : t("interview.wrongAccount.bodyNoEmail")}
      </p>
    </Message>
  );
}

function RoleLine({ link }: { link: InterviewLink }) {
  return (
    <p className="text-[15px] leading-[22px] text-ink-muted">
      {t("interview.roleAt", { title: link.job_title, company: link.company.name })}
    </p>
  );
}

/** One state: an optional icon, the heading, its text and at most one action. */
function Message({
  icon,
  title,
  meta,
  action,
  children,
}: {
  icon?: ReactNode;
  title: string;
  meta?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <>
      {icon && (
        <span
          aria-hidden="true"
          className="flex size-12 items-center justify-center rounded-md bg-surface-sunk text-ink [&_svg]:size-6"
        >
          {icon}
        </span>
      )}
      <div className="flex flex-col gap-3">
        <h1 className="type-display-lg break-words">{title}</h1>
        {meta}
      </div>
      <div className="type-body flex flex-col gap-4 text-ink">{children}</div>
      {action && <div className="flex">{action}</div>}
    </>
  );
}

function Alert({ children }: { children: ReactNode }) {
  return (
    <p
      role="alert"
      className="flex gap-2.5 rounded-md border border-signal-gap bg-surface-raised px-3.5 py-3 text-[14px] leading-5"
    >
      <WarningCircleIcon
        aria-hidden="true"
        className="mt-px size-[18px] shrink-0 text-signal-gap"
      />
      {children}
    </p>
  );
}
