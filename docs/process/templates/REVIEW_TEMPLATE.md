# Review: <TASK-ID> — round <N>

| Field | Value |
|---|---|
| PR | <link> |
| Reviewer | Claude (fresh session) / <name> |
| Date | YYYY-MM-DD |
| Verdict | Approve / Changes requested |

## Summary
<2–3 sentences: what the PR does and overall quality.>

## Acceptance criteria
| Criterion | Met? | Notes |
|---|---|---|
| … | ✓ / ✗ | |

## Findings
| # | Severity | File:line | Finding | Suggested fix |
|---|---|---|---|---|
| 1 | Blocking / Should fix / Nit | | | |

Severity guide: **Blocking** = bug, security/tenancy issue, data loss, AC not met, DoD violation. **Should fix** = maintainability or UX issue worth fixing now. **Nit** = optional.

## Checks
- [ ] Tenancy & permissions
- [ ] G1–G9 impacts handled
- [ ] Important functional tests present and passing (not coverage)
- [ ] Branch created from `develop`; PR targets `develop`
- [ ] Every commit has a description (What / Why / Task)
- [ ] PR description complete in the standard format
- [ ] Design match (screens compared with frame/spec)
- [ ] Docs updated

## Follow-ups
<Anything out of scope → new task IDs.>
