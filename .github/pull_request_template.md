<!--
PR title format: <type>(<branch-name>): <task title>   e.g. feature(auth-creation): Employer sign-in
Base branch: develop (feature/fix/refactor/… branches). Release PRs use docs/process/templates/RELEASE_PR_TEMPLATE.md.
Fill in every section. Write "None" instead of deleting a section.
-->

## Summary
<!-- 2–4 sentences: what this PR does and why, in plain language. -->

## Task and references
- **Task:** <TASK-ID> — `docs/tasks/<EPIC>/<file>.md`
- **Branch:** `feature/<short-name>` (created from `develop`)
- **Design:** <canvas frame name / SCREEN_SPECS S-xx / A-xx / None>
- **Requirements:** <FR-… / NFR-…>
- **ADRs followed or added:** <ADR-… / None>
- **Review file:** `docs/reviews/<TASK-ID>-r1.md` (added by the reviewer)

## Type of change
- [ ] Feature
- [ ] Fix
- [ ] Refactor / performance
- [ ] Tests only
- [ ] Docs only
- [ ] Chore / CI / config

## What changed
<!-- Group by area. List the important files or modules and what changed in each. -->
**Web (`apps/web`):**
- 

**API / worker (`apps/api`):**
- 

**Database (`supabase/migrations`):**
- 

**Docs:**
- 

## How it was tested
**Manual testing** (done before writing unit tests):
1. <step>
2. <step>
- [ ] Checked at 360 px (phone)
- [ ] Checked at 768 px (tablet)
- [ ] Checked at 1024 px and 1440 px (desktop)
- [ ] Checked as each affected role (Admin / Recruiter / Hiring manager / Candidate)

**Unit tests added** (important functional behaviour only):
- <test name — what it protects>

**Commands run:** `make lint` ✅ · `make test` ✅

## Screenshots / recordings
<!-- Required for UI changes: phone and desktop at minimum. Use sample data only — no real candidate data. -->
| Phone (360 px) | Desktop (1440 px) |
|---|---|
|  |  |

## Acceptance criteria
<!-- Copy from the task file and tick each one. -->
- [ ] 
- [ ] 

## Database, API and configuration
- **Migrations:** <None / file names + what they do + backward compatible? yes/no>
- **API changes:** <None / endpoints added or changed> — API client regenerated: <yes / not needed>
- **New or changed env vars:** <None / NAME — purpose — set in dev/QA/prod?>
- **Third-party setup needed:** <None / e.g. Stripe price, OAuth redirect URL>

## Security, tenancy and fairness
- [ ] New endpoints are workspace-scoped and have a tenancy test
- [ ] Permissions match `docs/architecture/SECURITY.md`
- [ ] No personal data in URLs, logs or error reports
- **Gap areas touched (G1–G9):** <list + how they're handled / None>
- **Compliance or bias impact:** <None / describe>

## Risks and rollback
- **Risks:** <what could break, who is affected>
- **Rollback:** <revert the PR / feature is unlinked / migration rollback steps>

## Follow-ups
<!-- Out-of-scope work discovered, with new task IDs if created. -->
- None

## Checklist
- [ ] Branch created from `develop`; PR targets `develop`
- [ ] Every commit has a subject and a description (`docs/process/GIT_CONVENTIONS.md` §3)
- [ ] Definition of Done met (`docs/process/DEFINITION_OF_DONE.md`)
- [ ] Task file updated (branch name, log, ticked criteria) and `docs/tasks/BOARD.md` status set to In review

<!-- If an AI tool created this PR, end with a line crediting it, e.g.: 🤖 Generated with [Claude Code](https://claude.com/claude-code). Commits never carry AI co-author lines. -->
