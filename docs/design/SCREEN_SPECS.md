# Screen specs (not in the canvas)

Text wireframes for screens and changes the MVP needs but the canvas doesn't show (ADR-018). Build them **in the same visual language** as the nearest canvas frame named in each spec: same shell, tokens, components, spacing and tone. Copy here is final unless marked *[placeholder]*.

Status: all **Specified** (not drawn in the canvas). Like every screen, these are built mobile first ([`RESPONSIVE.md`](RESPONSIVE.md)); the layouts below describe the desktop end state unless a mobile note is given.

---

## New screens

### S-01 Interview link landing and states — `/interview/[token]` (candidate side)
Base: `DemoDeviceCheck` header ("{Company logo} {Company} · interviews with FastHyr"), candidate surface, centred card on `surface-raised`, `radius-lg`, max 640 px, one primary persimmon button.

| State | Heading (display-lg) | Body | Primary action | Secondary |
|---|---|---|---|---|
| **Welcome** (valid, not started) | "Hi {first name}, ready for your interview?" | Role title · company. "This is a conversation with an AI interviewer about your experience and the {Job.title} role. It takes about 20–30 minutes. You can ask it questions about the role at any time." Bullets: "Find a quiet place with good light" · "Use Chrome, Edge, Safari or Firefox" · "{Video + voice: Your camera and microphone will be on / Voice only: Only your microphone is used}" · "Your link is open until {expiry}". Small print: "A person on the {Company} team makes every hiring decision. [How AI is used in this interview]" | "Check my camera and mic" (→ device check) | quiet: "I need an accommodation" → mailto company careers/website contact *[placeholder until a company contact field exists]* |
| **Resume** (abandoned, still valid) | "Welcome back, {first name}" | "You've already covered some of the interview. We'll pick up where you left off. You have about {minutes} minutes left." | "Continue my interview" | — |
| **Not signed in** | "Sign in to start your interview" | "Use the same Google or Microsoft account you applied with ({masked email e.g. p•••@gmail.com})." | "Continue with Google" / "Continue with Microsoft" (two secondary-style provider buttons as on Apply) | — |
| **Wrong account** | "This interview belongs to another account" | "You're signed in as {email}. Sign out and sign in with the account you used to apply." | "Sign out and switch account" | — |
| **Expired** | "This interview link has expired" | "The link was open until {expiry}. If you'd still like to interview, reply to the invitation email or contact {Company}." | none | link to company website |
| **Completed** | "You've finished this interview" | "Thanks, {first name}. Your answers are with the {Company} hiring team. You'll hear from them, not from us." | none | — |
| **Unavailable** (pipeline cancelled / application rejected) | "This interview is no longer available" | "The {Company} team has closed this step. If you have questions, contact them directly." | none | — |
| **Technical problem** (3 failed connections) | "We couldn't connect you" | "It's not you — something went wrong on our side or with the connection. Your link still works until {expiry}; try again in a few minutes, ideally on another network or browser." | "Try again" | — |

Device check reuses `DemoDeviceCheck` without the demo format toggle and "Leave demo" link. Consent area has **two** checkboxes when video + integrity checks are on:
1. (required) "I understand I'll be talking with an AI interviewer and that this session is recorded and shared with the {Company} hiring team."
2. (required for video + integrity) "I agree that FastHyr may compare my face across this session to confirm it's the same person. Face data isn't stored after the check. [Learn more]"
Voice-only pipelines show only checkbox 1. The words come from the versioned notices (COMP-002); the API sends `face_check` with the link. Before the browser prompt the page explains it ("Your browser will ask to use your camera and microphone. Choose Allow. Nothing is recorded or sent anywhere during this check."); a blocked permission shows fix steps for the browser. Until the live interview exists (INTV-005), Start shows "You’re all set".

### S-02 Interview end screen — within `/interview/[token]`
Base: `DemoInterview` done state. Heading "Thanks for the conversation, {first name}." Body: "Your interview is with the {Company} hiring team now. You'll hear from them by email — usually within a few days." Then the existing rating block (1–5 + optional comment, "isn't shared with the hiring team"). While the recording is still uploading, show above the heading: progress bar "Saving your interview… {n}%" and "Please keep this page open for a moment." — the page must not say "done" until uploads finish. No marketing CTAs.

### S-03 Human review request — `/review-request/[token]` (candidate side, no sign-in; token from rejection email)
Base: S-01 card layout.
- Heading: "Ask for a person to review your application"
- Body: "Your application for {Job.title} at {Company} was reviewed with the help of AI. You can ask a member of the {Company} hiring team to look at it again."
- Optional textarea: "Anything you'd like them to know? (optional)" hint "For example, experience that isn't clear from your résumé." max 1,000 chars.
- Primary: "Request a review". Success state: "Request sent. The {Company} team will review your application and email you with the outcome." Already requested: "You've already asked for a review. We'll email you when it's done." Expired (> 30 days after the email): "This link has expired…" with company contact.

### S-04 Join a workspace — `/join/[code]` (TA side)
Base: `WorkspaceSelect` layout, single card (the "Join" card enlarged).
- Signed out → redirect to `/login?next=/join/{code}`.
- Valid invite for this email: workspace avatar + name, "{Inviter} invited you to join {Workspace} as {Role}." Departments chips. Primary "Join {Workspace}" → Getting started / Overview.
- Invite for a different email: "This invite was sent to {masked email}. Sign in with that email to accept it." + "Log out".
- Expired/revoked: "This invite has expired" / "This invite is no longer valid" + "Ask your workspace admin to send a new one."
- Already a member: redirect to the workspace.

### S-05 Set a new password — `/reset-password`
Base: `EmployerLogin` split layout (evergreen panel left). Right: "Choose a new password"; "New password" (min 8, show/hide), "Confirm password"; primary "Save password" → signed in → `/workspaces`. Invalid/expired link: "This link has expired or was already used." + "Send a new link" (opens the forgot-password modal).

### S-06 Verify your email — `/verify-email`
Base: `EmployerLogin` right column. "Check your email" · "We sent a link to {email}. Open it on this device to verify your address and continue." Resend (60 s cooldown, same pattern as reset modal) · "Use a different email" (logs out).

### S-07 Pricing — `/pricing`
Base: `TalentAcquisition` page style.
- Hero: label "Pricing" · display-lg "Pay for applicants, not seats." · body "Every plan includes unlimited team members, pipelines and AI interviews. One applicant uses one credit."
- Trial banner: "Start with 20 free credits. No card needed." CTA "Let's get started".
- Three plan cards (Starter $99 / 80 credits / "For small teams hiring for a few roles at a time."; **Growth** $299 / 300 / "For teams running several pipelines every month." — "Most popular" label; Scale $799 / 1,000 / "For high-volume hiring across many roles."). Each: "/ month", "{n} plan credits every month", "Plan credits reset monthly".
- Extra credits table: 100 $160 · 250 $375 · 500 $700 (save 13%) · 1,000 $1,300 (save 19%) — "last 12 months".
- "Everything included" list: résumé screening, adaptive AI interviews (video + voice or voice only), explainable scores, integrity checks, Ask Ava, hiring insights, candidate emails, credits per pipeline.
- FAQ (accordion): What counts as a credit? · What happens when a pipeline runs out? · Do unused credits roll over? · Can I change plans? · Is there a contract? *[placeholder: month-to-month]* · Do you integrate with my ATS? ("No. FastHyr works through your apply link, so there's nothing to integrate.")
- Prices read from the API/config, not hard-coded.

### S-08 Terms, Privacy, AI in hiring — `/terms`, `/privacy`, `/ai-in-hiring`
Base: long-form article layout on `surface`, max width 720 px, `body` text, `heading` sections, table of contents on desktop. Content from counsel *[placeholder]*. `/ai-in-hiring` (plain-language, candidate-facing): what FastHyr does, what the AI looks at and ignores, recordings and who sees them, integrity checks, human decisions and how to request review, accommodations, retention and deletion, contact.

---

## Additions to existing frames

### A-01 Wizard step 1 — nice-to-haves and résumé pass bar (NewPipeline, ADR-013)
After "Résumé must-haves": **"Nice-to-haves (optional)"** chip input with "Hidden from candidates" pill and hint "Extra skills or experience that add to the résumé score but aren't required." Then **"Résumé pass bar"**: slider 0–100 (default 60) with value "60 / 100" and hint "Résumés at or above this score, with every must-have, are invited to interview. Most teams start at 60." Review step shows both rows under Role.

### A-02 Advance action (PipelineView candidates menu, CandidateProfile header — ADR-017)
- Row menu (Ready for review, or Flagged with all flags resolved): "Advance to next round" above "Reject candidate".
- Profile header: primary evergreen button "Advance to next round" next to "Email candidate" (hidden for hiring managers).
- Dialog: title "Advance {name}?" · body "They'll move to Advanced in this pipeline. FastHyr doesn't schedule the next round — you'll arrange it with them." · optional "Note for your team" textarea · checkbox (default on) "Email the candidate with your "Moving to the next stage" template." · buttons "Cancel" / "Advance candidate".
- Stage pill "Advanced" (evergreen-soft). New filters "Advanced" and "Rejected" in the Candidates tab.

### A-03 Review requested (PipelineView, CandidateProfile, Overview — ADR-015)
- Candidates tab: filter "Review requested {n}"; row badge "Review requested" (marigold-outline pill, ink text).
- Profile: banner on top of Overview (or Résumé tab for résumé decisions): "{name} asked for a person to review this decision on {date}." + candidate message in a quote block + buttons "Uphold decision" / "Invite to interview" (résumé) or "Move to Ready for review" (interview). Both require a note ("Only your team sees this"). Upholding sends no new email in MVP (the rejection already went out) *[confirm]*; overriding sends the invitation (résumé) or nothing (interview).
- Overview "Needs your attention": "{n} review requests" → Candidates tab filtered.

### A-04 Flag review panel (CandidateProfile — ADR-016)
On Overview's "Integrity checks" card when flags exist: each flag row (label, times as jump-to buttons, confidence as words "Likely / Possible") with guidance text (FRAUD_INTEGRITY.md §3) and a segmented control "No concern" / "Concern confirmed" + note, "Save review". Profile header shows "Flagged · {n} to review" until resolved. When face checks didn't run: row "Face check not run (no biometric consent or voice-only)".

### A-05 Delete candidate data (CandidatePool drawer, Admin only — FR-COMP-05)
Drawer footer quiet destructive link "Delete candidate data". Dialog: "Delete all of {name}'s data?" · "This removes their applications, résumés, recordings, transcripts and assessments from every pipeline in {Workspace}. You can't undo this." · reason select (Candidate request / Retention / Other) · type-to-confirm "delete" · "Delete data". Afterwards counts stay in dashboards but the person is gone.

### A-06 Billing without a plan (BillingInvoices — ADR-004)
When the workspace has no subscription: plan card becomes "You're on the free trial" with "{n} trial credits left · expire {date}" and plan picker cards (same as Change plan dialog) with "Choose {plan}" → Stripe Checkout. Credits card lists trial credits as its own row "Trial credits · used after plan credits". No invoices → empty state "No invoices yet".

### A-07 Email templates — three new templates (EmailTemplates — FR-MSG-01)
Add cards: "Interview received" (label "Confirmation", "Right after the interview"), "Role closed" (label "Update", "When you close a pipeline and choose to let candidates know"), "Human review received" (label "Update", "When a candidate asks for a person to review a decision"). Filter chips gain "Updates". Rejection templates show a locked footer line in the editor: "Want a person to review this decision? [Review.link]" with hint "This line is always included so candidates can ask for a human review."
"Moving to the next stage" timing text changes to "When you advance a candidate".

### A-08 Getting started copy (ADR-010)
Step 4 body: "Add a payment method and choose a plan. Each applicant uses 1 credit, so top up before applicants start arriving. You have {n} free trial credits to start." Step 5 body: "Paste a job description, pick the must-haves, and set the résumé pass bar. You choose video + voice or voice only."

### A-09 Demo setup — aligned settings (Demo — ADR-012)
Step 3 shows the wizard's settings: format, tone (Warm / Professional / Direct), seniority (Entry / Mid-level / Senior / Lead), focus areas (skills to probe) chips. Remove interviewer styles, 7-tone select and language select. Side note: "Demo interviews last up to 10 minutes and aren't recorded."

### A-10 For candidates page without listings (Candidates — ADR-018)
Keep hero (without search), "How FastHyr works for you" and the three benefit cards; replace the job list with a card: "Looking for a role? Apply through the job post on LinkedIn, JobStreet, Indeed or the company's careers page. If the company uses FastHyr, the Apply button brings you here." Copy change: "we read your résumé and build questions about your actual work" (no "6–10"). Nav label "For candidates".
