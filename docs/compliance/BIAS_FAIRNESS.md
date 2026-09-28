# Bias and fairness (G2)

## 1. Commitments (shown to candidates and customers)
- Name, photo, address, age, gender, graduation year and school name are **never used** to score a résumé or an interview.
- Candidates are scored against the **same locked criteria** for a pipeline (setup locks on open).
- Every score is **explained** with evidence; nothing is a black box.
- **A person decides.** AI recommends; flags never reject; automated rejections can be reviewed by a person.

## 2. Controls by stage
| Stage | Control |
|---|---|
| Pipeline setup | Must-haves and skills are job-related free text; wizard hint text discourages proxies ("culture fit", "native speaker", "young and dynamic", degree from specific schools). A text-model lint (post-MVP) can warn on risky criteria. "Also open to" widens access. |
| Résumé screen | Two-pass PII redaction before scoring (`AI_PIPELINE.md` §1); must-haves accept related/transferable evidence; code (not the model) computes the score; unreadable résumés are never auto-rejected. |
| Interview | Same topics structure for everyone in a pipeline (plan seeded from résumé but covering all skills to probe); interviewer instructions forbid protected-topic questions; candidates can ask to repeat/rephrase; voice-only option per pipeline; captions for accessibility; accent, appearance and background are not scored (explicit in scoring prompt). |
| Scoring | Criteria defined as job-related behaviours; evidence required per criterion; low temperature; prompt versioning; rubric snapshot stored with each assessment. |
| Integrity | Flags need human review; thresholds tuned to minimise false positives; accessibility-related behaviours (e.g. reading from notes due to disability) addressed in reviewer guidance on the flag panel. |
| Ava | Protected-attribute guard; sources for every claim; cannot act. |
| Outcomes | Human-review route; decision log. |

## 3. Evaluation (before every prompt/model change)
`apps/api/tests/ai_eval/` holds:
- **Counterfactual résumé pairs:** identical experience, different names (varied ethnicity/gender signals), schools, graduation years, addresses. Requirement: redaction removes the differences; résumé scores within **±3 points**; pass/fail identical.
- **Transcript pairs:** same answer content with different speech patterns (non-native phrasing, filler words). Requirement: communication scores within ±5 points when content is equivalent.
- **Golden sets:** expected score ranges for strong/average/weak candidates per role family.
- Results are attached to the PR that changes a prompt (`process/DEFINITION_OF_DONE.md`).

## 4. Monitoring in production
- Monthly **fairness report** (internal): pass rates by source, by "Also open to" group, and — once opt-in self-reported demographics exist (post-MVP) — by demographic group, with the four-fifths (80%) rule as an alert threshold.
- Track human-review outcomes: override rate by decision type is a quality signal.
- Track integrity-flag rates and "No concern" resolution rates to tune thresholds.

## 5. Documentation for customers
"How FastHyr's AI works" page/PDF: what data is used, what is ignored, how scores are computed, human oversight, known limitations (English only, SSO sign-in, audio quality), how to request review — supports customers' EU AI Act and NYC LL144 duties.
