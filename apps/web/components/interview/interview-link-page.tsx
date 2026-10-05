import type { DeviceCheckNotices } from "@/components/interview/device-check";
import { InterviewFlow } from "@/components/interview/interview-flow";
import type { SignInProblem } from "@/lib/apply/session";
import { devToolsEnabled } from "@/lib/env";
import type { InterviewLink } from "@/lib/interview";

/**
 * The interview link page (S-01, FR-INTV-02): the employer's name with "interviews with FastHyr"
 * (frame DemoDeviceCheck's header) over one centred card for the link's state, then the device
 * check and the live interview. Mobile first: the card fills the width with the page gutter, up
 * to 640 px.
 */
export function InterviewLinkPage({
  token,
  link,
  notices,
  signedInEmail,
  signInProblem,
}: {
  token: string;
  link: InterviewLink;
  /** The device check's consent texts (open links only). */
  notices: DeviceCheckNotices | null;
  /** The Google or Microsoft account signed in on this device, for the wrong-account state. */
  signedInEmail: string | null;
  /** Why the last sign-in came back without a session. */
  signInProblem: SignInProblem | null;
}) {
  return (
    <InterviewFlow
      token={token}
      link={link}
      notices={notices}
      signedInEmail={signedInEmail}
      signInProblem={signInProblem}
      // The scripted stand-in for OpenAI (the API's AI_FAKE=1): local and development only.
      allowFake={devToolsEnabled}
    />
  );
}
