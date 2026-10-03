import { CompanyMark } from "@/components/apply/company-mark";
import { TurnMark } from "@/components/brand/turn-mark";
import { InterviewLinkCard } from "@/components/interview/interview-link-card";
import type { SignInProblem } from "@/lib/apply/session";
import { t } from "@/lib/i18n";
import type { InterviewLink } from "@/lib/interview";

/**
 * The interview link page (S-01, FR-INTV-02): the employer's name with "interviews with FastHyr"
 * (frame DemoDeviceCheck's header) over one centred card for the link's state. Mobile first: the
 * card fills the width with the page gutter, up to 640 px.
 */
export function InterviewLinkPage({
  token,
  link,
  signedInEmail,
  signInProblem,
}: {
  token: string;
  link: InterviewLink;
  /** The Google or Microsoft account signed in on this device, for the wrong-account state. */
  signedInEmail: string | null;
  /** Why the last sign-in came back without a session. */
  signInProblem: SignInProblem | null;
}) {
  const { company } = link;
  return (
    <div className="flex min-h-dvh flex-col bg-surface">
      <header className="border-b border-line">
        <div className="page-gutter flex min-h-16 items-center gap-3 py-3 md:min-h-[72px]">
          <CompanyMark company={company} size="sm" />
          <p className="min-w-0 text-[14px] leading-5 text-ink-muted md:text-[15px]">
            <span className="font-semibold break-words text-ink">{company.name}</span>
            {" · "}
            {t("interview.interviewsWith")}{" "}
            <span className="inline-flex items-center gap-1 align-bottom">
              <TurnMark size={14} />
              <span className="font-display font-semibold text-ink">{t("site.name")}</span>
            </span>
          </p>
        </div>
      </header>

      <main className="page-gutter flex flex-1 flex-col items-center pt-6 pb-12 md:pt-12 lg:justify-center lg:pt-0 lg:pb-18">
        <InterviewLinkCard
          token={token}
          link={link}
          signedInEmail={signedInEmail}
          signInProblem={signInProblem}
        />
      </main>
    </div>
  );
}
