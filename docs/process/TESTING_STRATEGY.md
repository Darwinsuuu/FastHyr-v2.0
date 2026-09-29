# Testing strategy

Two rules keep testing useful without slowing us down.

## 1. Write unit tests after the feature works
1. Build the feature.
2. Test it by hand (locally, then on the development environment after merge if needed) until it behaves as the acceptance criteria say.
3. **Then** write the unit tests, as the last step on the feature branch (usually its last commit).

Why: while a feature is still changing, tests written early have to be rewritten with every change. Writing them once the behaviour is settled costs far less.

## 2. Test only the important functional behaviour
Write tests for **what the feature must do**, not for every line or case. Aim for a small number of tests that would catch a real regression.

**Always test (these are important):**
- Core business rules: state transitions (pipelines, applications, interviews), résumé pass rule, score calculation, credit operations (grant, reserve, consume, release, expiry).
- Money and credits: anything that charges, grants or consumes.
- **Tenancy and permissions** for new endpoints: another workspace's data returns 404; department and role limits hold. A leak here is the worst possible bug, so this stays mandatory.
- Security-sensitive logic: token checks, PII redaction, email HTML sanitising, protected-attribute guard in Ava.
- Bugs that were fixed: one test that reproduces the bug.

**Skip:**
- UI rendering and styling details, simple components, snapshot tests.
- Getters, setters, pure wiring, framework behaviour.
- Exhaustive edge-case matrices — cover the main path and the one or two failures that matter.
- Unit tests for third-party SDKs (test our wrapper's important behaviour with fakes instead).

## 3. Other test types
| Type | When |
|---|---|
| Manual testing | Every feature, before writing unit tests, at phone (360 px), tablet (768 px) and desktop (1440 px) widths; QA on the release environment before production, including a real phone |
| AI evaluation (`tests/ai_eval/`) | When a prompt or model changes (fairness checks in `compliance/BIAS_FAIRNESS.md`) |
| End-to-end (Playwright, `apps/web/e2e/`, `make e2e` against `make dev`) | Only the few core journeys: employer email sign-in (AUTH-001), password reset (AUTH-002); the rest added in REL-001. Runs in CI on every PR (FND-006) |

## 4. In the task file
Each task's **Test plan** lists only the important functional tests. The reviewer checks that they exist and pass, not that coverage is high.
