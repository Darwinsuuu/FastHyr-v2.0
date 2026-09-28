# AI-in-hiring regulations

> **Not legal advice.** This is an engineering summary so we build the right safeguards. Laws and their effective dates change; confirm every item with counsel before launch (ROADMAP OQ-3, OQ-4). Last reviewed: 2026-09-29.

FastHyr screens résumés, interviews candidates with AI, scores them and sends automated outcomes. In most jurisdictions that makes it an **automated employment decision tool** and, in the EU, a **high-risk AI system**. FastHyr is usually the *provider/vendor*; the hiring company is the *deployer/employer* — both carry duties, and customers will expect us to support theirs.

## Summary of obligations → what we build

| Law / framework | Key duties (simplified) | FastHyr safeguard |
|---|---|---|
| **GDPR / UK GDPR** | Lawful basis; transparency; data minimisation; rights of access, erasure, objection; **Art. 22** limits on solely automated decisions with significant effects (need safeguards: human intervention, contest the decision); DPIA for high-risk processing; processor contracts (DPA) | Consent + notices (FR-COMP-01); human-review route on every automated rejection (ADR-015); decision log; deletion within 30 days (FR-COMP-05); DPA template; sub-processor list; DPIA before EU launch |
| **EU AI Act** | AI used for recruitment/selection is **high-risk** (Annex III). Provider duties: risk management, data governance, technical documentation, logging, transparency to deployers, human oversight design, accuracy/robustness, conformity assessment, registration. Deployer duties: human oversight, inform candidates, keep logs. Obligations phase in; **verify current application dates** (possible postponements). | Human-in-the-loop by design (flags never reject; review route; TA decides), `ai_decisions` + `ai_calls` logs, versioned prompts and evaluation sets (technical documentation), deployer-facing "How FastHyr's AI works" doc, candidate notices |
| **NYC Local Law 144 (AEDT)** | Independent **bias audit** within one year before use, public audit summary, notice to NYC candidates ≥ 10 business days before use, info on data collected, alternative process on request | Decide whether to allow NYC roles at launch (OQ-4). If yes: commission audit, publish summary, add NYC notice text on apply page, "request an alternative process" contact |
| **Illinois AI Video Interview Act** | Before the interview: notify that AI may analyse the video, explain how it works and what characteristics it evaluates, obtain consent; limit sharing; delete videos within 30 days of request; (if relying solely on AI to decide who gets an in-person interview) collect/report demographic data | Device-check consent text with explanation link (`/ai-in-hiring`), recordings shared only with the employer's permitted members, deletion within 30 days |
| **Illinois BIPA** (and similar biometric laws, e.g. Texas, Washington) | Written notice, purpose and retention schedule, written consent before collecting biometric identifiers (face geometry, voiceprints) | Face checks only with explicit biometric consent; embeddings never stored (ADR-016); retention schedule published in Privacy Policy |
| **Illinois Human Rights Act amendment (AI)** | Notice when AI is used in employment decisions; no discriminatory use | Candidate notices; bias monitoring |
| **Colorado AI Act** | Duties for developers and deployers of high-risk AI (consequential decisions incl. employment): impact assessments, notices, adverse-decision explanations and appeal. **Verify effective date.** | Adverse-decision emails include reason category + review link; documentation for deployers |
| **US EEOC / Title VII, ADA** | Employer liable for disparate impact of tools; reasonable accommodation for disabilities | Bias monitoring (`BIAS_FAIRNESS.md`); accessibility (WCAG 2.2 AA); accommodation contact in candidate notices (voice-only option exists per pipeline; candidates can contact the employer) |
| **CCPA/CPRA** (California) and ADMT regulations | Notice at collection, rights to know/delete/correct; rules on automated decision-making technology incl. pre-use notice and opt-out/appeal in employment contexts | Notice at collection on apply page; deletion flow; review route |
| **Other privacy laws** (PDPA SG, PDPA MY, PH Data Privacy Act, Indonesia PDP, Canada PIPEDA/Quebec Law 25, Brazil LGPD, Australia Privacy Act) | Consent/notice, cross-border transfer rules, breach notification, access/deletion | Same baseline controls; sub-processor and transfer disclosures in Privacy Policy; breach-response runbook |

## Product rules that follow from this
1. A person makes every hiring decision. AI outputs are labelled as recommendations.
2. Every automated rejection offers a human review (ADR-015).
3. Candidates are told, before applying and before the interview, that AI is used, what it evaluates (job-related skills and communication from their résumé and answers), that the session is recorded, who sees it, how long it's kept and how to ask for review, accommodation or deletion.
4. Protected characteristics are never inputs to scoring and never used by Ava (G2).
5. Integrity flags never reject on their own (G7).
6. We keep logs (decisions, model and prompt versions) long enough to explain any decision (retain `ai_decisions` for the life of the application + 3 years; minimal record after candidate deletion — confirm with counsel).
7. Customers get: DPA, sub-processor list, "How FastHyr's AI works" documentation, bias-monitoring summary.

## Launch gates
- [ ] Counsel review of Terms, Privacy Policy, AI-in-hiring notice, consent texts, DPA.
- [ ] Jurisdiction decision (OQ-4) and any required audits.
- [ ] DPIA completed.
- [ ] Bias evaluation run on the release prompts (`BIAS_FAIRNESS.md`).
