# Source: Claude Project instructions (verbatim)

> Raw input, copied as given on 2026-09-27. Do not edit; the structured docs under `docs/` are derived from this.
> Related sources: Claude Design canvas "FastHyr UI/UX Design" (https://claude.ai/artifact/5K5XeumMMTTgj4f37pzwvW)
> and "FastHyr Design System" (https://claude.ai/artifact/1zb54CSHVs2p3tV1dTM1mt).

---

## Product Overview

FastHyr is a B2B SaaS AI interviewer platform built for Talent Acquisition (TA) teams. The primary user is the HR/TA professional, not the candidate. TA teams create a job description and build a hiring pipeline. Each pipeline gets its own shareable apply link, which the TA team pastes into their job posts on LinkedIn, JobStreet, Indeed, or their careers page. From that point, FastHyr handles everything: resume analysis, AI interview generation, and candidate assessment — automatically, at scale.

## Core Workflow

1. **Pipeline Creation** — TA user creates a job description and configures a hiring pipeline with pass/fail thresholds, required skills, and interview tone/depth.
2. **Shareable Apply Link** — Each pipeline generates a unique apply link. TA teams use it as the external Apply URL on their job posts (e.g., on LinkedIn they use the Apply button instead of Easy Apply). Candidates who click Apply are redirected straight to FastHyr. There is no ATS or job-board integration.
3. **Resume Analysis** — FastHyr analyzes the candidate's resume (PDF only) against the job description to check qualification fit.
4. **Screening Gate** — If the candidate passes the resume screen, they proceed. If not, they're filtered out with optional auto-rejection messaging.
5. **Personalized Interview Plan** — For passing candidates, FastHyr prepares a tailored interview plan based on the JD and their specific resume.
6. **AI Interview** — The candidate completes an async, adaptive AI interview by video + voice or voice only. The AI interviewer asks follow-up questions based on the candidate's answers and responds to their questions the way a human interviewer would.
7. **Candidate Assessment** — FastHyr scores and summarizes the interview, delivering a structured assessment report to the TA user.

## Users & Their Goals

- **TA / HR (Primary)** — Reduce time-to-screen, ensure every applicant is assessed consistently, get structured feedback without manual effort.
- **Hiring Manager (Secondary)** — View shortlisted candidates and their AI-generated assessments; make faster decisions.
- **Candidate (End user, not customer)** — Complete a fair, clear, low-anxiety interview experience; receive timely feedback.

## Tone & Design Direction

Warm, professional, and reassuring — especially for candidate-facing surfaces. TA-facing surfaces can lean more data-dense and efficient.

## Known Gaps & Product Considerations

These are active areas that must be accounted for in design, engineering, and product decisions. When working on any feature, check whether it intersects with one of these concerns.

### 1. Candidate Drop-off & Re-engagement
Candidates who start but don't finish the AI interview are a conversion and data loss problem. The product needs a re-invite flow, configurable expiry logic per pipeline, and drop-off rate tracking visible in the TA dashboard. Every incomplete interview should surface a reason code where possible (timed out, abandoned, link expired).

### 2. Bias & Fairness Layer
AI-generated questions and scoring can encode bias. FastHyr needs a bias audit trail, question diversity checks across demographic-neutral language, and clear EEO compliance positioning for enterprise clients. Resume analysis must not use signals like name, address, or graduation year as scoring factors.

### 3. Interview Configuration Depth
Interview format must be configurable per pipeline, not global. TA users choose the interview modality: video + voice, or voice only (there is no text interview). Every interview is adaptive — there is no fixed question count and no per-question timer. The AI builds its questions from the resume and job description and follows up on the candidate's answers like a human interviewer. TA users can still shape the interview through tone, depth, required skills to probe, and difficulty calibration.

### 4. Assessment Rubric Ownership
TA users must define what "pass" means for the AI interview stage. FastHyr should support configurable scoring weights per pipeline (e.g., communication 30%, technical fit 50%, culture alignment 20%). Opaque AI scoring with no TA control will lose trust. Score breakdowns must be explainable, not just a number.

### 5. Candidate Feedback & Rejection Messaging
After the AI interview, every candidate expects a response. FastHyr needs templated and AI-generated rejection and advancement messaging that TA users can customize, schedule, or auto-send. Ghosting candidates is a brand risk for the hiring company. Timing and tone of messaging should be configurable.

### 6. Multi-Stage Pipeline Support
FastHyr is typically stage 1, but most hiring processes have multiple stages. TA users need to move candidates forward to human interviews, technical assessments, or offers — ideally within the same pipeline view. FastHyr should natively support stage progression within the pipeline view.

### 7. Fraud & Impersonation Prevention
Candidates may have someone else complete their AI interview. For roles where integrity matters, FastHyr needs proctoring signals suited to video and voice interviews: liveness detection and face matching (video), identity verification, and behavioral anomaly flags such as a second voice or person detected, unusual response latency, answers that sound read aloud or prompted, or the candidate leaving the camera frame. At minimum, FastHyr needs a flag system TA users can review and act on — flags never auto-reject a candidate. This is a trust and compliance concern for enterprise clients.

### 8. TA Dashboard & Analytics
The dashboard is the primary value delivery layer for TA leadership to justify the tool. It must surface: time-to-screen per pipeline, pass/fail rates, candidate drop-off rates, source quality comparison (LinkedIn vs. JobStreet vs. others, tracked through a source tag on the apply link), question performance (which questions differentiate candidates), and pipeline throughput over time. Reports must be exportable.

### 9. Human Interview Scheduling
When a candidate advances past the AI interview, TA users need an easy way to schedule the next human round (e.g., sharing a booking link or sending a calendar invite). No ATS or HRIS integrations are planned.

## How Claude Should Help in This Project

- Default to the TA user's perspective when designing flows or writing copy, unless the context is explicitly candidate-facing.
- When suggesting features, always flag which of the gap areas above it intersects with.
- When writing product copy, match the warm and professional tone — avoid cold, robotic, or overly technical language.
- When reviewing or generating code, assume a SaaS multi-tenant architecture where pipeline data, candidate data, and assessment data are scoped per organization.
- Raise compliance and bias implications proactively when they're relevant, even if not asked.
- FastHyr does not integrate with any ATS. Candidates reach FastHyr only through a pipeline's shareable apply link. Don't suggest ATS connections, ATS sync, or ATS webhooks.
