# Source: Design canvas inventory

> Raw record of what the Claude Design canvas **"FastHyr — Product Design"** contains, read frame by frame on 2026-09-29.
> Canvas: https://claude.ai/artifact/5K5XeumMMTTgj4f37pzwvW · Design system: https://claude.ai/artifact/1zb54CSHVs2p3tV1dTM1mt
>
> This file records **what the design shows**, including its inconsistencies. Where the design disagrees with itself, the resolution is in `docs/decisions/`, not here. Names, numbers and people in the frames are sample data.

The canvas has 23 frames (1440 px wide) in 8 sections. The frame file name is given in brackets; use it when referring to a frame.

---

## 01 Public website

### Main landing `[Main.dc.html]`
- Nav: For Employers, Find Jobs, Pricing (`#`, no page), "See a live demo".
- Hero: "Automate first-round interviews. Keep the process fair." CTAs to employer page and job list.
- Two-sided sections (TA teams / candidates), a product tour with 5 tabs (Overview, Pipeline, Candidate profile, AI interview, Ask Ava) showing screenshots, "Every applicant, heard" comparison, 4-step "How it works", 6 feature cards (Résumé screening, Adaptive AI interview, Scores you can explain, Integrity checks, Ask Ava, Hiring insights), footer (Privacy, Terms, Contact: all `#`).

### Talent acquisition landing `[TalentAcquisition.dc.html]`
- Nav: Home, For Candidates, Pricing (`#`), "Let's get started" → Employer login. "Try our demo" → Demo.
- Animated example of one applicant: applied through link with `?source=linkedin` → résumé checked → AI interview → "91 of 100" with rubric Technical fit 50 / Communication 30 / Culture 20.
- 4 steps; 9 feature cards incl. **Candidate emails**, **Candidate profiles** (history across applications), **Credits per pipeline** ("One applicant uses one credit, and unused credits come back when a pipeline closes").
- Contact block: email hello@fasthyr.com, "Start a chat" (`#`), social links, **contact form** (Name, Work email, Company, How can we help?).

### For candidates `[Candidates.dc.html]`
- Public job board: search, location filter, filters (Function with counts, Work type, Location), job cards with company, location, tags, salary range, "Apply for this role", "Load 20 more roles".
- Copy says "we read your résumé and build **6–10 questions**" and "most people finish in 20–30 minutes".

### Apply to a role `[Apply.dc.html]` (interactive)
- Header: employer logo/name "Acme Talent Careers · Hiring with FastHyr"; Sign in / signed-in menu (name, email, "Signed in with Google", Sign out).
- Banner "Accepting applications · closes Fri, 26 Feb 2027"; title; meta chips (department, employment type, work setup, location).
- JD sections; "Coming from a different path?" block listing the pipeline's "Also open to" options; "How applying works" (3 steps); fairness note ("Your name, photo, address, age and graduation year are never used…"); "Role at a glance" facts (Department, Employment type, Work setup, Location, Interview format, Applications close); About the company card (industry, size, HQ, website, other roles).
- **Sign-in modal: Google or Microsoft only** ("No password to create").
- **Application form modal**: Résumé* (PDF only, upload/replace/remove), Full name*, Email (from SSO, verified), Contact number* (country code select + number), Current city (optional), LinkedIn or portfolio (optional), **consent checkbox*** (review with FastHyr, AI interview by video and voice, recorded and shared with hiring team, Privacy Policy link). Validation messages; "Send application".
- Success modal "Application sent" with 3 next steps; page then shows "Applied on {date}" and "Your application is in".

## 02 Interview demo

### Demo setup `[Demo.dc.html]`
- 3 steps: (1) Job description: templates (Product designer, Backend engineer, Support specialist, Paste my own) + textarea; (2) Résumé: upload PDF ≤10 MB or "Use sample résumé", parsed preview (experience, skills matched, education, "Name, address and graduation year are hidden from scoring"), "deleted when you leave"; (3) Configure interviewer: format (Video + voice / Voice only), **interviewer style** (Friendly guide, Balanced professional, Rigorous expert, Stress tester), **tone** (7 options), **language** (English, Filipino, Taglish), focus areas chips derived from the JD.
- Side recap "Your interview"; "Always adaptive… No fixed question list or timer."

### Camera & mic check `[DemoDeviceCheck.dc.html]`
- Format toggle (demo only). Camera check: preview with face outline, "Wave at the camera", "Detect my wave" → "Camera working". Mic check: read a sentence aloud, level meter → "Microphone working". Voice-only shows mic check only.
- Consent checkbox: "I understand I'll be talking with an AI interviewer and that this session is recorded and shared with the {Company} hiring team." "Start interview" enabled only when checks pass and consent is ticked.

### AI interview `[DemoInterview.dc.html]`
- Header: "{Company} · interviews with FastHyr", **"Time remaining" countdown (20 min in the demo)**, "Live · {role}", Leave demo.
- Stage: interviewer status (Listening…, Following up on your answer, Answering your question, then moving on), current AI line, "From your résumé: {quote}", live captions / scrolling transcript, Mute/Unmute, End interview, self-view "camera and mic on".
- Side: "What we'll talk about" topic list with progress; "Good to know" tips.
- End: "Thanks for the conversation" + **experience rating 1–5 + optional comment** ("isn't shared with the hiring team").

## 03 Employer sign-in

### Employer login `[EmployerLogin.dc.html]`
- Continue with Google, Continue with Microsoft, or Work email + Password. "New here? Sign in with your work email and we'll set up your account."
- **Forgot password modal**: email, validation, "Send reset link"; sent state (link works once, expires in 1 hour, from no-reply@fasthyr.com), resend after 60 s; note that SSO users have no password.
- Terms / Privacy links.

### Choose workspace `[WorkspaceSelect.dc.html]`
- "Welcome, {name}. Where will you be hiring?" Two cards: **Create a workspace** (Workspace name) and **Join a workspace** (invite link or code, e.g. `fasthyr.com/join/AB12-CD34`).
- User menu: User profile, Log out. **User profile modal**: email (Verified), signs in with (Google), last signed in, account created, user ID (copy); name/photo come from Google.

## 04 Dashboard

### App shell (all TA screens)
- Sidebar: workspace switcher (list of workspaces with the user's role and member count; Create / Join a workspace), Getting Started, Overview, Pipelines, Candidates; **Billing & usage**: Billing & invoices, Credit usage; **Workspace admin**: Company profile, Departments, Manage members, Email templates. User menu (name, "Admin · Acme Talent", User profile, Log out).

### Getting started `[GettingStarted.dc.html]`
- Checklist: (1) Set up company profile, (2) Invite your team (optional), (3) Customize candidate email templates (optional), (4) **Set up billing and buy credits** ("Each completed AI interview uses credits" — conflicts with other screens), (5) Create your first pipeline ("set the résumé pass threshold").
- Welcome video card, "Watch tutorials", "Sit in the candidate's chair" → Demo.

### Overview `[Overview.dc.html]`
- Greeting, "View pipelines", "New pipeline".
- KPIs (This week / 30 days): Applicants (+delta), Ready for review (+flagged), Live pipelines (paused, scheduled), Median time to screen.
- **Needs your attention**: candidates ready for review, flagged interviews, pipeline paused out of credits, pipeline running low, plan credits expiring, invites not accepted.
- Funnel: Applied → Résumé matched → Finished the AI interview → Passed the interview; median time to screen; interview completion %.
- Strongest candidates waiting (score, Strong/Good fit); Live pipelines closing soonest; Applicants per week (8 weeks, applied vs passed); Where applicants come from (source, count, pass rate); Why interviews go unfinished (link expired, left partway, camera/mic problems); Credits card (available, reserved, free, plan credits used, plan + renewal); quick links.

## 05 Pipeline journey

### Pipelines `[PipelinesV2.dc.html]`
- Flow summary (Applied → Invited → Interviewed → Ready for review) with details (processing, not a match, in progress, not started, flagged, didn't pass); "Reports" (generates PDF); "New pipeline".
- Tabs Live / Scheduled / Closed / All; search; table: owner avatar, title, department, status (Live, Paused · out of credits, Paused, Scheduled, Completed, Closed, Cancelled), candidates, "N to review", credits used/total bar, days remaining; pagination.
- Row menus by status — Live: Open, Copy apply link, View setup, Pause, Close. Out of credits: Top up credits, Open, Copy link, Close. Paused: Resume, Open, Copy link, Close. Scheduled: Edit setup, Start now, Copy link, Cancel. Closed: View results, Archive.
- Modals: **Pause** (link stops accepting, countdown continues, current candidates carry on), **Close** (+ checkbox to email "Role closed" template), **Cancel scheduled** (reserved credits return), **Archive** (moves out of list, data kept), **Share apply link** (LinkedIn, JobStreet, Indeed, Kalibrr, Glassdoor, Facebook, Careers page, Other → copies `https://fasthyr.com/apply/{company}/{role}?source={id}` with per-board hints), **report generation progress** ("Please don't close or refresh this window", steps, Download PDF).

### Pipeline creation `[NewPipeline.dc.html]` — 5-step wizard
1. **Role**: Job title, Department (optional, default "No department"), Employment type (Full-time, Part-time, Contract, Internship), Work setup (On-site/Hybrid/Remote), Location, Job description (shown to candidates, used for screening and planning), **Résumé must-haves** (hidden from candidates, min 3), **Also open to** (Fresh graduates, Career changers, Returning to work, No degree required, Ready for a step up, Relocating or remote-first), fairness note.
2. **AI interview**: Format (Video + voice / Voice only), note "no fixed number of questions and no timer per question", Tone (Warm, Professional, Direct), Seniority and depth (Entry, Mid-level, Senior, Lead), **Skills to probe** (hidden, min 3), Interview link expires after (3/5/7/14 days), toggles: reminder 24 h before expiry, flag possible impersonation.
3. **Scoring**: rubric sliders Technical fit / Communication / Culture alignment (must sum to 100), Pass mark (0–100; at/above = "Recommended"), toggles: email résumé-not-a-match candidates (next working day), email candidates after their interview.
4. **Schedule & credits**: Open now / Schedule a date; duration 30/60/90/120 days ("Pausing doesn't extend this date"); **Reserve interview credits** (min 10, ±10, warns if more than free credits; "1 applicant = 1 credit, used when someone applies"; runs out → pauses; leftovers return on close).
5. **Review** and publish; confirm by typing "I understand"; **setup locks when the pipeline opens** (scheduled pipelines stay editable until opening). Save as draft. After publish: share-link tiles, "Create another".

### Pipeline details `[PipelineView.dc.html]`
- Header: title, status, department, format, opened date, owner; "Share apply link". Tabs: Dashboard, Candidates (count), Ask Ava, Setup.
- **Dashboard**: KPIs (candidates, ready for you, time to assessment, credits used, days remaining), funnel, new applicants per day (14 days), interview score histogram with pass mark, sources table (applicants, pass rate), didn't-finish reasons (link expired, left mid-interview, technical issue) with **"Re-invite all"**.
- **Candidates**: stage filters (All, Processing résumé, Résumé not a match, Invited to interview, Interview in progress, Ready for review, Didn't pass interview, Flagged); search; table (candidate, stage, fit status Strong ≥80 / Good ≥ pass mark with tooltip, source, applied); row menu: View profile, Download résumé, Download candidate report (if interviewed), Review flag (if flagged), Email candidate (mailto), **Reject candidate** (required reason visible to team only, optional email with "Rejection" template). **No "advance" action.**
- **Ask Ava**: pipeline-scoped assistant with suggested questions, tables, cited sources, "What Ava can see", "How Ava stays fair"; refuses to compare on protected attributes.
- **Setup**: read-only cards (role, AI interview, scoring, schedule & credits) with "Duplicate as new pipeline".

## 06 Candidates

### Candidates (pool) `[CandidatePool.dc.html]`
- "Everyone who's applied to {workspace}", **view only** ("To act on a candidate, open them in their pipeline"). Tabs: Dashboard, Candidate list, Ask Ava (workspace-wide).
- Dashboard: KPIs, new candidates per month, applications per candidate, where applications ended up, best sources, most common skills.
- List: filters (All, Applied more than once, Interviewed, Passed an interview), search by name/email/skill, table (applications count + Returning badge, latest role and stage, best score, last applied).
- Profile drawer: applications, interviews, best score, latest assessment summary, score over time, Ava's summary, skills, application history with links.

### Candidate profile `[CandidateProfile.dc.html]`
- Header: name, email, applied date and source, stage, fit, link to all applications, Email candidate, Download candidate report. Tabs: Candidate overview, Résumé, AI interview.
- **Overview**: overall score /100 vs pass mark, rank, pipeline average, evidence count, integrity status; **"How we got to 91"** (criterion score × weight); **Why each score** (sub-signals + evidence quotes with interview timestamps or résumé), "Held it back"; distribution, comparison, topic scores vs average, history across applications, **Ava's summary** with numbered references, strengths, worth probing next round, résumé match, answer patterns, **integrity checks** (face matched, one voice, stayed in frame, natural timing), journey timeline, fairness note.
- **Résumé**: fit score /100 vs **screening bar 60**, decision, screened time, time to screen, rank; **"How we got to 88"**: Must-haves 40% + **Nice-to-haves 20%** + Relevant experience 25% + Skill depth 15%; career snapshot; PDF viewer with highlights (must-have / nice-to-have / impact); must-have evidence; nice-to-haves found; measurable impact; résumé claims checked in the interview; experience timeline; comparison; note on hidden fields (name, photo, address, age, gender, graduation year, school name).
- **AI interview**: stats (length, questions, follow-ups, talk time, format), video player with topic markers, topics covered with scores (click to seek), searchable transcript (click to seek).

## 07 Billing & usage

### Billing & invoices `[BillingInvoices.dc.html]`
- Plan card: Starter $99 / 80 credits, **Growth $299 / 300**, Scale $799 / 1,000 per month; renewal date; card; Change plan; Manage subscription.
- Credits: plan credits used first (expire at month end, don't roll over), extra credits next (each purchase lasts 12 months), expiry table in use order.
- Payment method (card), billing details (company, billing email, address, tax ID), invoices table (Plan / Credits kind, status Paid/Open/Failed) with detail modal and PDF ("Getting the invoice from Stripe"); "Payments are processed securely by Stripe".
- **Buy extra credits**: 100 / $160, 250 / $375, 500 / $700 (save 13%), 1,000 / $1,300 (save 19%), pay with saved card.
- **Change plan**: upgrade takes effect today with proration and raises this month's plan credits; downgrade at next renewal.

### Credit usage `[CreditUsage.dc.html]`
- "Each applicant uses 1 credit from the reserve of the pipeline they applied to. Plan credits are used first, then extra credits, oldest purchase first."
- KPIs (available, used this month, reserved, free to reserve), split bar, credits per month (plan vs extra vs allowance), usage by department, alerts for pipelines out of / low on credits, per-pipeline table (status, reserve used, left, this month, outlook) with **Add credits** modal (+25/50/100/200 from free credits), credit activity ledger.

## 08 Workspace admin

### Company profile `[CompanyProfile.dc.html]`
- Logo (SVG/PNG, square, ≥256 px, ≤2 MB), email banner (PNG/JPG 1200×400, ≤2 MB), company name*, website; industry, company size, HQ country, time zone; about your company (≤600 chars), careers page URL.

### Departments `[Departments.dc.html]`
- Stats; table (name, description, pipelines by status, candidates, who can see it, created); built-in **No department** (admins only); add/edit (unique name, "No department" reserved), delete (pipelines move to No department; members lose that access).

### Manage members `[ManageMembers.dc.html]`
- Members / Pending invites tabs; filters by role and department; table (member, role, departments, last active, status); edit access (role + departments), remove access.
- Invite modal: email, role (Recruiter, Hiring manager, Admin), departments. **Invites expire after 7 days**; resend (new link, old stops working), revoke.
- Roles: **Admin** — billing, members, company profile, every pipeline. **Recruiter** — creates and edits pipelines, reviews all candidates and assessments in their departments. **Hiring manager** — views shortlisted candidates and their assessments for roles they're assigned to; can't edit pipelines.

### Email templates `[EmailTemplates.dc.html]`, Edit email template `[EditEmailTemplate.dc.html]`
- 6 default templates: Interview invitation (right after the résumé passes), Interview reminder (24 h before expiry), Finish your interview (when left unfinished), Moving to the next stage (**when a candidate passes the AI interview**), Not moving forward — résumé (2 business days after screening), Not moving forward — interview (3 business days after the interview).
- Parameters: `[Candidate.firstname]`, `[Candidate.lastname]`, `[Job.title]`, `[Company.name]`, `[Interview.link]`, `[Interview.expiry]`.
- Editor: subject, rich text (bold, italic, link, bullets), insert parameter, reset to default, save, send test to me, change history with view/restore.
- Other templates referenced elsewhere but not listed: "Role closed" (close pipeline modal), post-interview email (wizard toggle "lets them know it's being reviewed").

---

## Inconsistencies found (resolved in ADRs)

| Topic | Design says | Resolution |
|---|---|---|
| Credit consumption | On apply (wizard, credit usage, TA landing) vs "each completed AI interview" (Getting started) | ADR-010 |
| Scores vs signals | DS: "never a single number" vs 91/100 everywhere | ADR-011 |
| Interview length | "6–10 questions", "Question 3 of 8" vs no fixed count; 20-min demo timer | ADR-012 |
| Résumé pass rule | Profile shows bar 60 + nice-to-haves; wizard has neither | ADR-013 |
| Candidate sign-in | Google / Microsoft only | ADR-014 |
| Automated rejection emails | Sent without human involvement | ADR-015 |
| Face match | No reference photo collected | ADR-016 |
| Advancement | Auto email on pass; no advance action | ADR-017 |
| Job board, Ava naming, demo settings, missing screens | — | ADR-018 |
