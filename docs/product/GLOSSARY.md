# Glossary

Use these words exactly, in code, UI copy and docs. Don't invent synonyms (no "job", "requisition", "opening" for a pipeline; no "org" or "tenant" in UI copy for a workspace).

| Term | Meaning | Code name |
|---|---|---|
| **Workspace** | A company's (or team's) FastHyr account. The tenant. Holds pipelines, candidates, members, billing. A user can belong to several. | `workspace` |
| **Member** | A TA user in a workspace, with a role. | `workspace_member` |
| **Role** | Admin, Recruiter or Hiring manager. Per membership. | `role`: `admin` \| `recruiter` \| `hiring_manager` |
| **Owner** | The Admin who created the workspace. Cannot be removed. | `is_owner` |
| **Department** | Optional grouping of pipelines inside a workspace; also scopes member access. | `department` |
| **No department** | Built-in bucket for pipelines without a department. Admins only. | `department_id IS NULL` |
| **Invite** | Email invitation to join a workspace, with role and departments. Expires after 7 days. | `invite` |
| **Pipeline** | One role being hired for: job details, screening rules, interview setup, rubric, schedule, credit reserve, apply link. | `pipeline` |
| **Apply link** | Public URL of a pipeline's apply page: `fasthyr.com/apply/{workspace-slug}/{pipeline-slug}`. | — |
| **Source tag** | `?source=` value on the apply link (linkedin, jobstreet, indeed, kalibrr, glassdoor, facebook, careers, other). | `application.source` |
| **Must-haves** | Hidden criteria every résumé is checked for (min 3). | `pipeline.must_haves` |
| **Nice-to-haves** | Optional hidden criteria that add to the résumé fit score. | `pipeline.nice_to_haves` |
| **Also open to** | Candidate groups the pipeline welcomes without the usual track record. | `pipeline.open_to` |
| **Résumé pass bar** | Minimum résumé fit score to be invited to interview (default 60). | `pipeline.resume_pass_bar` |
| **Skills to probe** | Hidden skills the AI interviewer must cover (min 3). | `pipeline.skills_to_probe` |
| **Rubric** | Three weighted criteria — Technical fit, Communication, Culture alignment — summing to 100%. | `pipeline.weights` |
| **Pass mark** | Minimum overall interview score to be "Ready for review". | `pipeline.pass_mark` |
| **Publish** | Make a pipeline live or scheduled. Locks the setup once it opens. | — |
| **Locked** | A pipeline whose setup can no longer change (from the moment it opens). | `pipeline.locked_at` |
| **Candidate** | A person who applied to a workspace. One record per person per workspace. | `candidate` |
| **Application** | One candidate applying to one pipeline. Has a stage. | `application` |
| **Stage** | Where an application is: Processing résumé, Résumé not a match, Invited to interview, Interview in progress, Ready for review, Didn't pass interview, Advanced, Rejected (plus link expired / left unfinished sub-states). See `WORKFLOW.md`. | `application.stage` |
| **Flagged** | An interviewed application with at least one unresolved integrity flag. Shown as its own filter. | derived |
| **Review requested** | The candidate asked for a human review of an automated rejection. | `human_review_request` |
| **Résumé fit score** | 0–100 score from the résumé screen. | `resume_assessment.score` |
| **Interview plan** | Topics and résumé-anchored question seeds prepared for one candidate. | `interview_plan` |
| **AI interviewer** | The voice that interviews candidates. Never called "Ava". | — |
| **Interview** | One candidate's AI interview session(s) for an application, with recording and transcript. | `interview` |
| **Interview link** | Personal link emailed to an invited candidate: `fasthyr.com/interview/{token}`. Expires after the pipeline's expiry days. | `interview.token` |
| **Drop-off reason** | Why an interview wasn't finished: Link expired, Left mid-interview, Technical issue. | `interview.drop_reason` |
| **Assessment** | The scored result of an interview: overall, per-criterion scores, evidence, summary. | `assessment` |
| **Evidence** | A quote from the interview (with timestamp) or résumé that supports a score. | `assessment.evidence` |
| **Signal** | Evidence strength label: Strong evidence, Worth probing, Not evidenced yet. Labels evidence, never replaces a score. | `signal` |
| **Fit** | Badge on passed candidates: Strong fit (≥80, all must-haves) or Good fit (≥ pass mark). | derived |
| **Integrity flag** | A possible-impersonation signal (different face, second voice, read aloud, unusual timing, left frame). Never rejects on its own. | `integrity_flag` |
| **Advance** | Manual TA action moving a candidate to the next (off-platform) round and sending the next-stage email. | stage `advanced` |
| **Ava** | FastHyr's TA assistant that answers questions about candidates in a pipeline or workspace. | `ava` |
| **Credit** | Unit of usage. 1 applicant = 1 credit. | `credit` |
| **Plan credits** | Credits included with a monthly plan; expire at the end of the billing period; used first. | batch kind `plan` |
| **Extra credits** | Credits bought as a pack; expire 12 months after purchase; used after plan credits, oldest first. | batch kind `extra` |
| **Trial credits** | One-time 20 credits for a new workspace; expire after 30 days. | batch kind `trial` |
| **Reserve** | Credits a pipeline sets aside; only that pipeline can use them; unused credits return on close. | `pipeline.credits_reserved` |
| **Free credits** | Workspace balance not reserved by any open pipeline. | derived |
| **Credit ledger** | Append-only record of every credit change. | `credit_ledger` |
| **Email template** | Workspace-editable candidate email with parameters like `[Candidate.firstname]`. | `email_template` |
| **Demo** | Public try-it-yourself interview on the marketing site, not tied to a workspace. | `demo_session` |
