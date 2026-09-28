# Cross-cutting considerations (gap areas G1–G9)

These come from the project instructions. **Every user story and task must list which of G1–G9 it touches**, and every design or code review must check them.

| ID | Area | MVP status | Where it's handled |
|---|---|---|---|
| **G1** | Candidate drop-off & re-engagement | **In MVP** | Link expiry per pipeline, 24 h reminder, "Finish your interview" email, resume-later, "Re-invite all", drop-off reason codes (link expired, left mid-interview, technical issue) on Overview and Pipeline dashboard |
| **G2** | Bias & fairness | **In MVP** | PII redaction before scoring (name, photo, address, age, gender, graduation year, school name), fixed job-related criteria, evidence required per score, Ava refuses protected attributes, AI decision log, bias monitoring report — `compliance/BIAS_FAIRNESS.md` |
| **G3** | Interview configuration depth | **In MVP** | Per pipeline: format (video+voice / voice only), tone, seniority, skills to probe, link expiry, integrity toggle. Adaptive, no question count, no per-question timer, 30-min session cap (ADR-012) |
| **G4** | Assessment rubric ownership | **In MVP** | Editable weights (sum 100), pass mark, résumé pass bar and nice-to-haves (ADR-013), every score shows its calculation and evidence (ADR-011) |
| **G5** | Candidate feedback & messaging | **In MVP** | 6 designed templates + "Interview received", "Role closed", "Human review received"; editor with parameters, history, test send; business-day scheduling; human-review link in rejections (ADR-015) |
| **G6** | Multi-stage pipeline support | **Partial** | Only a manual **Advance** action + next-stage email (ADR-017). Stages after FastHyr are post-MVP |
| **G7** | Fraud & impersonation | **In MVP (scoped)** | Same-account sign-in for the interview; same-face, second-voice, read-aloud and timing flags; flags never auto-reject (ADR-016) |
| **G8** | TA dashboard & analytics | **In MVP** | Overview, Pipelines flow, Pipeline dashboard, Candidates dashboard, Credit usage; PDF reports. "Question performance" analytics is post-MVP (topic scores are captured so it can be built later) |
| **G9** | Human interview scheduling | **Post-MVP** | Next-stage email can include the team's booking link as text; no calendar integration |

## Standing rules (from the project instructions)
- No ATS, ATS sync or ATS webhooks — ever. Candidates arrive only through apply links.
- Default to the TA perspective except on candidate-facing surfaces.
- Copy is warm and professional; never cold, robotic or overly technical.
- All pipeline, candidate and assessment data is scoped per workspace.
- Raise compliance and bias implications proactively.
