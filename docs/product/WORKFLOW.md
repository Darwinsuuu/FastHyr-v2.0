# Core workflow and state machines

This is the authoritative description of how a pipeline and an application move through FastHyr. Code must implement exactly these states and transitions; any change needs an ADR.

## 1. End-to-end flow

```
TA side                                   FastHyr                                   Candidate side
───────                                   ───────                                   ──────────────
1. Create pipeline (wizard) ──publish──▶  pipeline scheduled/live
2. Share apply link (?source=…)  ──────────────────────────────────────────────▶  sees job post, clicks Apply
                                                                                    3. Signs in (Google/Microsoft),
                                          ◀──────────────────── application ────── uploads PDF résumé, consents
                                          1 credit used from pipeline reserve
                                          4. Résumé screen (fit score vs pass bar)
                                             ├─ not a match ──▶ rejection email (2 business days, human-review link)
                                             └─ match ────────▶ interview plan + invitation email ──▶ 5. opens link
                                                                                    device check + consent
                                          6. AI interview (Realtime, ≤30 min)  ◀──▶  talks with AI interviewer
                                          7. Transcribe, score, integrity checks
                                             ├─ below pass mark ─▶ "didn't pass" (+ email after 3 business days)
                                             └─ at/above ───────▶ Ready for review (Strong/Good fit)
8. Review profile, evidence, flags ◀────
9. Advance (email) or Reject (reason) ─────────────────────────────────────────▶  next-stage or rejection email
```

## 2. Pipeline states

| State | Apply link | Setup editable | Shown as |
|---|---|---|---|
| `draft` | Not reachable (404) | Yes | (not in list; "Save as draft" in wizard) |
| `scheduled` | Shows "Opens on {date}" | Yes, until `opens_at` | Scheduled |
| `live` | Accepts applications | No (locked) | Live |
| `paused` | "Not taking applications right now" | No | Paused |
| `paused_no_credits` | Same as paused | No | Paused · out of credits |
| `closed` | "This role is closed" | No | Completed (closed on schedule) / Closed (closed by hand) |
| `cancelled` | 404 | — | Cancelled |

`archived_at` is a separate flag on `closed`/`cancelled` pipelines: hidden from the Pipelines list, data kept.

Transitions:
- `draft → scheduled` (publish with a future date) · `draft → live` (publish now)
- `scheduled → live` (cron at `opens_at`, or "Start now") · `scheduled → cancelled` (reserve returned)
- `live → paused` (manual) · `paused → live` (resume)
- `live → paused_no_credits` (reserve used up, or workspace balance hits 0) · `paused_no_credits → live` (credits added)
- `live | paused | paused_no_credits → closed` (manual close, or cron at `closes_at`). Unused reserve returns to free credits.
- Pausing never extends `closes_at`.
- Candidates already in the pipeline carry on through screening and interviews in every state except `cancelled`.

Lock rule: from the moment a pipeline is `live` (`locked_at` set), the Role, AI interview, Scoring and Schedule sections cannot change. Only pause/resume/close and credit top-ups are allowed. "Duplicate as new pipeline" copies the setup into a new draft.

## 3. Application stages

| Stage | Meaning | Candidate sees |
|---|---|---|
| `processing_resume` | Résumé uploaded, screening queued/running | "Your application is in" |
| `resume_not_match` | Fit score below pass bar or a must-have missing | Rejection email after 2 business days (if enabled) |
| `invited` | Passed screen; interview link sent | Invitation email |
| `interview_in_progress` | Interview started, not finished | Interview page |
| `scoring` | Interview finished; transcription/scoring running | "Thanks for the conversation" |
| `ready_for_review` | Overall score ≥ pass mark | (post-interview email if enabled) |
| `did_not_pass` | Overall score < pass mark | Rejection email after 3 business days (if enabled) |
| `advanced` | TA advanced the candidate (ADR-017) | "Moving to the next stage" email |
| `rejected` | TA rejected the candidate with a reason | Rejection email (if ticked) |

Sub-states on `invited` / `interview_in_progress` (stored on the interview, shown in drop-off analytics):
- `link_expired` — never started before expiry.
- `left_unfinished` — started, then left; can resume until the link expires ("Finish your interview" email).
- `technical_issue` — device check failed or connection lost repeatedly.

Overlays (not stages):
- **Flagged** — interview has ≥1 unresolved integrity flag. Shown under the "Flagged" filter instead of Ready for review / Didn't pass until resolved.
- **Review requested** — candidate asked for a human review (ADR-015).

Transitions:
```
processing_resume ─▶ resume_not_match ──(human review: override)──▶ invited
processing_resume ─▶ invited ─▶ interview_in_progress ─▶ scoring ─▶ ready_for_review ─▶ advanced
                       │                 │                          │        └────────▶ rejected
                       │                 │                          └─▶ did_not_pass ──(human review: override)──▶ ready_for_review
                       └── link expired / left unfinished ──(re-invite)──▶ invited (new link, same credit)
invited | interview_in_progress | ready_for_review ─▶ rejected (TA, reason required)
```
- `processing_resume` can also end in **`resume_unreadable`** handling: if no text can be extracted, the application stays in `processing_resume` with an error badge and the TA can reject or invite manually. (No automatic rejection for unreadable files.)
- Re-invite creates a new interview link; the application keeps its single credit.
- Rejected and advanced are terminal in MVP.

## 4. Interview session lifecycle
`not_started → in_progress → completed`, or `not_started → expired`, or `in_progress → abandoned → in_progress (resume) → completed`.
- A session may be resumed while the link is valid; the 30-minute cap counts total talk time across attempts.
- On resume, the AI interviewer receives a summary of the conversation so far and continues from the next topic.
- Completed is set when the candidate ends the interview, the interviewer wraps up, or the cap is reached.

## 5. Timings (defaults)
| Event | When |
|---|---|
| Résumé screen | Immediately after apply (target < 2 min) |
| Invitation email | Right after the résumé passes |
| Reminder email | 24 h before link expiry, if not started (pipeline toggle) |
| "Finish your interview" | 1 h after an abandoned session, if the link is still valid |
| Résumé rejection email | 2 business days after screening (workspace time zone) |
| Interview rejection email | 3 business days after the interview |
| Post-interview "we've got it" email | Right after the interview (pipeline toggle) |
| Invite (member) expiry | 7 days |
| Interview link expiry | 3 / 5 / 7 / 14 days (pipeline setting) |
