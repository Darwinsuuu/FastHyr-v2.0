"use client";

import { ApiError, createApiClient, unwrap } from "@fasthyr/api-client";
import {
  ArrowUpRightIcon,
  CheckCircleIcon,
  ClockCountdownIcon,
  LinkBreakIcon,
} from "@phosphor-icons/react";
import { useRouter } from "next/navigation";
import { type ReactNode, useState } from "react";

import { InterviewHeader } from "@/components/interview/interview-header";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Textarea } from "@/components/ui/input";
import { env } from "@/lib/env";
import { t } from "@/lib/i18n";
import {
  cardState,
  contactHref,
  MESSAGE_MAX,
  type ReviewCardState,
  type ReviewLink,
} from "@/lib/review-request";

const api = createApiClient({ baseUrl: env.apiUrl });

/**
 * S-03 (ADR-015): one centred card in the interview link page's layout. The candidate can ask a
 * person on the hiring team to look at their application again, with an optional message. Mobile
 * first: the card fills the width with the page gutter, up to 640 px.
 */
export function ReviewRequestPage({ token, link }: { token: string; link: ReviewLink }) {
  const router = useRouter();
  const [current, setCurrent] = useState(link);
  const [sentNow, setSentNow] = useState(false);
  // A server refresh (after a 409) brings a new link state.
  const [seen, setSeen] = useState(link);
  if (link !== seen) {
    setSeen(link);
    setCurrent(link);
  }

  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);

  async function send(message: string) {
    setPending(true);
    setFailed(false);
    try {
      const next = unwrap(
        await api.POST("/v1/public/review-requests/{token}", {
          params: { path: { token } },
          body: { message: message.trim() || null },
        }),
      );
      setCurrent(next);
      setSentNow(true);
    } catch (error) {
      // The link expired or the decision changed while the page was open: show why.
      if (error instanceof ApiError && error.status === 409) router.refresh();
      else setFailed(true);
    } finally {
      setPending(false);
    }
  }

  const state = cardState(current, sentNow);
  return (
    <div className="flex min-h-dvh flex-col bg-surface">
      <InterviewHeader company={current.company} tagline={t("reviewRequest.hiresWith")} />
      <main className="page-gutter flex flex-1 flex-col items-center pt-6 pb-12 md:pt-12 lg:justify-center lg:pt-12 lg:pb-18">
        <section className="flex w-full max-w-[640px] flex-col gap-6 rounded-lg border border-line bg-surface-raised p-6 shadow-raised md:p-10">
          {state === "open" ? (
            <RequestForm
              link={current}
              pending={pending}
              failed={failed}
              onSend={(message) => void send(message)}
            />
          ) : (
            <StateMessage link={current} state={state} />
          )}
        </section>
      </main>
    </div>
  );
}

function RequestForm({
  link,
  pending,
  failed,
  onSend,
}: {
  link: ReviewLink;
  pending: boolean;
  failed: boolean;
  onSend: (message: string) => void;
}) {
  const [message, setMessage] = useState("");
  const company = link.company.name;
  return (
    <form
      noValidate
      className="flex flex-col gap-6"
      onSubmit={(event) => {
        event.preventDefault();
        onSend(message);
      }}
    >
      <div className="flex flex-col gap-3">
        <h1 className="type-display-lg break-words">{t("reviewRequest.open.title")}</h1>
        <p className="type-body text-ink">
          {t("reviewRequest.open.body", { job: link.job_title, company })}
        </p>
      </div>
      <Field
        label={t("reviewRequest.open.messageLabel")}
        hint={t("reviewRequest.open.messageHint")}
      >
        <Textarea
          rows={5}
          maxLength={MESSAGE_MAX}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
        />
      </Field>
      {failed && (
        <p role="alert" className="text-[14px] leading-5 font-semibold text-signal-gap">
          {t("reviewRequest.open.failed")}
        </p>
      )}
      <div className="flex">
        <Button
          type="submit"
          side="candidate"
          size="lg"
          loading={pending}
          className="w-full sm:w-auto"
        >
          {t("reviewRequest.open.submit")}
        </Button>
      </div>
    </form>
  );
}

function StateMessage({
  link,
  state,
}: {
  link: ReviewLink;
  state: Exclude<ReviewCardState, "open">;
}) {
  const company = link.company.name;
  const href = contactHref(link.company);
  const contact =
    href && (state === "expired" || state === "unavailable") ? (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 text-[15px] font-semibold text-persimmon-ink underline hover:text-evergreen"
      >
        {t("reviewRequest.contact", { company })}
        <ArrowUpRightIcon aria-hidden="true" className="size-4" />
        <span className="sr-only"> {t("interview.newTab")}</span>
      </a>
    ) : null;
  const icon: Record<typeof state, ReactNode> = {
    sent: <CheckCircleIcon />,
    requested: <CheckCircleIcon />,
    expired: <ClockCountdownIcon />,
    unavailable: <LinkBreakIcon />,
  };
  return (
    <>
      <span
        aria-hidden="true"
        className="flex size-12 items-center justify-center rounded-md bg-surface-sunk text-ink [&_svg]:size-6"
      >
        {icon[state]}
      </span>
      <div className="flex flex-col gap-3">
        <h1 className="type-display-lg break-words">{t(`reviewRequest.${state}.title`)}</h1>
        <p className="type-body text-ink">
          {t(`reviewRequest.${state}.body`, { company, job: link.job_title })}
        </p>
      </div>
      {contact && <div className="flex">{contact}</div>}
    </>
  );
}
