<!--
Use for promotion PRs only:
  develop → release   title: "Branch Management: RELEASE Deployment DD.MM.YYYY"
  release → master    title: "Branch Management: PRODUCTION Deployment DD.MM.YYYY"
The merge commit uses the same title plus a What / Why description (GIT_CONVENTIONS.md §5).
-->

## Release summary
<!-- 2–3 sentences: what this release brings, in product terms. -->

## Promotion
- **From → to:** `develop` → `release` / `release` → `master`
- **Target environment:** QA / Production
- **Version tag (production only):** `vYYYY.MM.DD-N`
- **Overall change title (production only):** <e.g. Candidate intake and résumé screening>
- **Upcoming Changes file (production only):** `docs/releases/YYYY-MM-DD.md`

## Tasks included
| Task | Title | PR |
|---|---|---|
| <TASK-ID> | <title> | #<n> |

## Fixes included (`fix/`, `hotfix/`)
- None

## Database migrations (in order)
| Migration | What it does | Backward compatible |
|---|---|---|
| | | |

## Configuration to apply before or after deploy
- **Env vars:** <None / list per environment>
- **Third-party:** <None / Stripe, OAuth, Resend, Supabase Auth settings>

## QA results (required for `release` → `master`)
- **Tested by / date:**
- **Test run:** <link or summary; include phone and desktop checks>
- **Known issues accepted for release:** <None / list with task IDs>

## Deployment and rollback plan
- **Order:** migrations → API/worker → web
- **Smoke test after deploy:** <steps>
- **Rollback:** <steps>

## Checklist
- [ ] All included tasks are Done on `docs/tasks/BOARD.md`
- [ ] CI green on the source branch
- [ ] Every change in this release was merged into `develop` first (and into `release` first, for production PRs)
- [ ] Production only: Upcoming Changes file exists, is up to date and is listed in `docs/releases/README.md`
- [ ] Merge commit will use the PR title as its subject and include a What / Why description
