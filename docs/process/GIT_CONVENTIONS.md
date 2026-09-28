# Git conventions and branching

## 1. Long-lived branches
| Branch | Environment | Purpose | Who merges into it |
|---|---|---|---|
| `master` | **Production** | What customers use. Always stable. | `release` only |
| `release` | **Release / QA** | Candidate build for QA testing before production. | `develop` only |
| `develop` | **Development** | Integration and developer testing of finished work. | Working branches (`feature/`, `fix/`, `hotfix/`, …) only |

**All code changes go through `develop` first, then `release`, then `master`. No exceptions** — not for QA bugs, not for production bugs.
Never commit directly to these three branches; every change arrives by pull request, and nothing skips a step.

```
<prefix>/<short-name> ──PR──▶ develop ──PR (release)──▶ release ──PR (after QA sign-off)──▶ master
   (from develop)             (development)             (QA)                                (production)
```
Because every change travels the same one-way path, there are no back-merges: `develop` always contains everything that's in `release` and `master`.

## 2. Working branches

> **Rule: every new branch is created from `develop` — always.** Never branch off `release` or `master`.
> ```
> git checkout develop
> git pull origin develop
> git checkout -b feature/<short-name>
> ```
> This applies to every prefix, including `fix/` and `hotfix/`.

- One task = one working branch, named `<prefix>/<short-kebab-name>`, e.g. `feature/auth-creation`, `fix/apply-upload-retry`.
- Use the prefix that matches the **main purpose** of the work (table below). If a branch mixes purposes, split it or pick the dominant one.
- Record the branch name in the task file's **Log** section so the task and branch stay linked.
- Keep it short-lived; rebase on or merge its base branch if it falls behind. Delete it after merging.

### Branch prefixes
| Prefix | Use it for | Created from | Merged into | Example |
|---|---|---|---|---|
| `feature/` | New functionality from the task board | `develop` | `develop` | `feature/auth-creation` |
| `fix/` | A bug found in development **or by QA** on the release environment | `develop` | `develop` | `fix/apply-consent-error` |
| `hotfix/` | A bug found **in production** | `develop` | `develop` | `hotfix/stripe-webhook-timeout` |
| `refactor/` | Restructuring code without changing behaviour | `develop` | `develop` | `refactor/credits-service` |
| `perf/` | Performance improvements | `develop` | `develop` | `perf/pipeline-list-query` |
| `test/` | Adding or fixing tests only | `develop` | `develop` | `test/tenancy-candidates` |
| `docs/` | Documentation only | `develop` | `develop` | `docs/branching-rules` |
| `chore/` | Maintenance: dependencies, config, tooling, scripts | `develop` | `develop` | `chore/upgrade-nextjs` |
| `ci/` | CI/CD workflows and deployment config | `develop` | `develop` | `ci/add-migration-check` |

### How fixes reach each environment
| Bug found in | Branch | Path to production |
|---|---|---|
| Development (`develop`) | `fix/<name>` from `develop` | `develop` → next release → `master` |
| QA (`release`) | `fix/<name>` from `develop` | `develop` → `release` (re-test in QA) → `master` |
| Production (`master`) | `hotfix/<name>` from `develop` | `develop` → `release` (quick QA) → `master` as soon as it passes |

For an urgent production bug, open a release PR right after the hotfix is merged into `develop`, containing what's currently in `develop` (including the hotfix). If `develop` holds work that isn't ready for customers at that moment, keep that work unreachable (not linked in the UI) until it is — never let a change skip `develop` or `release`.

## 3. Commits
A branch has **one commit, or a few when the work has clearly separate steps**. Don't commit every small save; group work into meaningful steps.

Format:
```
<type>(<branch-name>): <what this step does>
```
- `<branch-name>` is the part after the prefix (e.g. `auth-creation`).
- The subject is in sentence case, says what the step does, and stays under ~72 characters.
- **Every commit has a description (body)** after a blank line. Never commit with a subject only.

### Commit description (required)
```
<type>(<branch-name>): <What this step does>

What:
- <main change>
- <main change>

Why:
- <reason / problem solved>

Notes: <migrations, env vars, follow-ups — omit the line if none>
Task: <TASK-ID>
```
- **What** lists the meaningful changes (not every file).
- **Why** explains the reason, so a reader understands the commit without opening the PR.
- **Task** links the commit to its task.
- **No AI co-authors.** Commits never include `Co-Authored-By` (or similar) trailers for Claude or any other AI tool. The person committing is the author.
- A commit template ships with the repo: run `git config commit.template .gitmessage` once per clone, then `git commit` (without `-m`) opens it.
- AI agents write the body with a heredoc or multiple `-m` flags; a one-line `-m` is not enough.

### Commit types
| Type | Use it for |
|---|---|
| `feature` | New functionality |
| `fix` | Bug fix found in development or QA |
| `hotfix` | Fix for a bug found in production |
| `refactor` | Code change that doesn't change behaviour |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `docs` | Documentation |
| `style` | Formatting only (no code meaning changes) |
| `chore` | Dependencies, config, tooling, scripts |
| `ci` | CI/CD and deployment config |
| `revert` | Reverting an earlier commit (mention the commit hash) |

The commit type usually matches the branch prefix, but a branch can contain other types when a step needs it — e.g. a `feature/` branch ends with a `test(...)` commit.

Examples — branch `feature/auth-creation` (subjects):
```
feature(auth-creation): Building authentication page
feature(auth-creation): Supabase auth integration
test(auth-creation): Implement unit test for authentication
```
Full example of one commit:
```
feature(auth-creation): Supabase auth integration

What:
- Connect Google, Microsoft and email sign-in buttons to Supabase Auth
- Add /auth/callback route that stores the session and redirects
- Route users to /workspaces or their last workspace after sign-in

Why:
- TA users need to sign in before they can create or join a workspace (FR-AUTH-01, FR-AUTH-04)

Notes: requires Google and Azure OAuth redirect URLs for each environment
Task: AUTH-001
```
Branch `hotfix/stripe-webhook-timeout`:
```
hotfix(stripe-webhook-timeout): Process Stripe events in the worker instead of the request
```
Branch `chore/upgrade-nextjs`:
```
chore(upgrade-nextjs): Upgrade Next.js and fix breaking changes
```
The last commit on a feature branch is usually the tests, because tests are written after the feature works (see [`TESTING_STRATEGY.md`](TESTING_STRATEGY.md)).

## 4. Pull requests
Every PR has a **detailed description in the standard format**. Empty or one-line PR descriptions are not accepted.

| PR | Template | Title format |
|---|---|---|
| Working branch → `develop` (feature, fix, refactor, …) | [`.github/pull_request_template.md`](../../.github/pull_request_template.md) — GitHub fills it in automatically | `<TASK-ID>: <task title>` e.g. `AUTH-001: Employer sign-in` |
| `develop` → `release` | [`templates/RELEASE_PR_TEMPLATE.md`](templates/RELEASE_PR_TEMPLATE.md) | `Release YYYY-MM-DD → QA` |
| `release` → `master` | [`templates/RELEASE_PR_TEMPLATE.md`](templates/RELEASE_PR_TEMPLATE.md) (QA results required) | `Release YYYY-MM-DD → Production (vYYYY.MM.DD-N)` |
| `fix/` or `hotfix/` → `develop` | PR template; mark type Fix; for hotfixes describe the production incident and its impact | `<TASK-ID or FIX/HOTFIX>: <what is fixed>` |

The standard PR description covers, in this order:
1. **Summary** — what and why, in plain language.
2. **Task and references** — task file, branch, design frame/spec, requirements, ADRs, review file.
3. **Type of change.**
4. **What changed** — grouped by web, API/worker, database, docs.
5. **How it was tested** — manual steps (at phone, tablet and desktop widths, per affected role), unit tests added, commands run.
6. **Screenshots** — phone and desktop for any UI change (sample data only).
7. **Acceptance criteria** — copied from the task and ticked.
8. **Database, API and configuration** — migrations, API changes and client regeneration, env vars, third-party setup.
9. **Security, tenancy and fairness** — tenancy tests, permissions, no PII, G1–G9 impact.
10. **Risks and rollback.**
11. **Follow-ups.**
12. **Checklist** — branch from `develop`, commit descriptions, Definition of Done, task file and board updated.

Write "None" for sections that don't apply rather than deleting them.

**PRs created by an AI tool** credit the tool as the creator on the last line of the description, e.g. `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. This is the only place AI attribution appears — never in commits.

**Merging:**
- Merge commit (no squash), so the branch's meaningful, described commits stay in history.
- Needs a passing CI run and an approved review (`DEV_WORKFLOW.md`).
- Tag production merges `vYYYY.MM.DD-N` (e.g. `v2026.10.15-1`).

## 5. Never commit
Secrets, `.env` files, customer data, or real candidate résumés/recordings. Test fixtures are synthetic.
