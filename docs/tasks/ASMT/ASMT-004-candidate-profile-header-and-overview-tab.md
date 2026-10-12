# ASMT-004: Candidate profile — header and Overview tab

| Field | Value |
|---|---|
| Epic | ASMT — Assessment & review |
| Milestone | M5 Review |
| Status | Done |
| Size | L |
| Depends on | [ASMT-001](../ASMT/ASMT-001-interview-scoring.md), [PIPE-008](../PIPE/PIPE-008-pipeline-details-candidates-tab.md) |
| Requirements | FR-ASMT-07 |
| Gap areas | G4 |
| Design | Frame CandidateProfile (Overview) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
TA users see how a score was reached, the evidence behind it and how the candidate compares.

## Scope
**In:**
- `GET /applications/{id}` payload
- Header (stage, fit, applications link, email, report, advance/reject)
- Overall score, 'How we got to', why each score with evidence jump links, distribution, comparisons, topics radar, history, Ava summary refs, strengths, probes, résumé match, answer patterns, integrity card, journey, fairness note

**Out:**
- —

## Acceptance criteria
- [x] Every evidence link seeks the recording
- [x] HM view read-only
- [x] No candidate PII in URL
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Auto-approved per the owner's standing rule, 2026-09-29.)_

**API**
- `GET /v1/applications/{id}` (`VIEW_CANDIDATES`): `services/application_profile.py` + `repositories/application_profile.py`. Pipeline outside the caller's departments, another workspace, a deleted candidate, or (Hiring managers) an application outside the shortlist (ready for review, flagged, advanced) → `404`. Payload `ApplicationProfile` (`schemas/application_profile.py`):
  - application (stage, `flagged`, `open_flags`, `review_requested`, fit, source, applied time), candidate (id, name, email), pipeline (id, title, status, pass mark, format, integrity on/off, `rubric_locked_at` = published), workspace name and time zone;
  - `resume`: status, fit score, pass bar, passed, must-haves met, screened time;
  - `interview`: latest interview's status, format, completed time, length, `recording_ready`, assessment and integrity status;
  - `assessment` (latest): overall, passed, fit, the three criteria (score, weight, points, signals, evidence with `start_ms` on the recording's clock, held back), topics (with the pipeline's average per topic), summary with numbered refs, strengths, probes, answer patterns, assessed time;
  - `comparison`, among every completed interview in the same pipeline (FR-ASMT-07; aggregates only, so Hiring managers get the same numbers): interviewed, rank (ties share a place), average, passed, distribution (<50, 50s … 90+), per-criterion average and passed average, answer-pattern averages. A topic's average is the mean score of the pipeline's topics of the same kind (warm-up, the candidate's questions) or covering the same skills to probe, since topic titles are personal;
  - `integrity`: status, which checks ran (`integrity_checks`), flags (type, times, confidence, status);
  - `history`: the person's applications in this workspace the caller can see (department scope, Hiring-manager shortlist), with pipeline, stage and score;
  - `journey`: applied, résumé screened, invited, interview finished, assessed, advanced/rejected, with times.
- `GET /v1/applications/{id}/recording-url` (same access): signed URLs (15 min) for the latest finished interview's recording and poster, `404 recording_not_ready` otherwise. Only the plain player needs it now; ASMT-006 builds on it.
- Seed: full assessment content for sample interviews (signals, evidence, topics, summary, strengths, probes, answer patterns, plan topics, integrity checks), with Bea Garcia's from the frame; `rubric_snapshot` in the stored shape.

**Web** (`/candidates/[candidateId]?application=&tab=overview|resume|interview`, `components/candidates/`, helpers in `lib/candidates/profile.ts`)
- Back link to the pipeline's Candidates tab; header: name, email, applied date and source, stage, fit, "Flagged · n to review", "N applications to {workspace}" (scrolls to History). Email candidate (mailto), Advance and Reject disabled until ASMT-007, Download candidate report disabled until ASMT-009; Hiring managers see only the report button (read-only). Below `md` the actions sit in a sticky bottom bar (Advance, Reject, More) per RESPONSIVE.md.
- Overview: overall score card, "How we got to" (kit `WeightedCalc`), Why each score (signals, evidence with time buttons or Résumé, held back), distribution, comparisons, topic radar vs average, history, summary with sources, strengths and probes, résumé match, answer patterns, integrity checks (flags with jump-to times, Likely ≥ 0.80 / Possible, guidance; resolving is ASMT-003), journey, fairness note. Before an assessment exists the tab says where the candidate is.
- Every interview time (evidence, summary refs, flags) goes to `?tab=interview&t=<seconds>`; the AI interview tab has a plain player (signed URL) that seeks to `t`. Topic markers, transcript and keyboard controls stay with ASMT-006; the Résumé tab says it's on its way (ASMT-005).
- Candidates tab: the name and "View profile" open the profile.
- Mobile first: one column at 360, two columns where the frame has them from `lg`.

**Tests**: profile payload and comparisons on a hand-counted set; Hiring-manager shortlist and department `404`s, other workspace via the tenancy harness; recording URL; web unit tests for the profile helpers.

## Log
- 2026-10-12: branch `feature/asmt-004-ytbfxl`; plan auto-approved.
- 2026-10-12: built and checked by hand on the seed at 360, 768, 1024 and 1440 px, light and dark, as an Admin and a Hiring manager (read-only), on an application with no assessment, and with a test recording in local Storage (evidence times open the AI interview tab at that second). The seed's recording paths had a stray `recordings/` prefix; they now use `recording_file_path()`. Advance, Reject and Download candidate report stay disabled until ASMT-007 and ASMT-009; the Résumé tab and the full AI interview tab say they're on their way (ASMT-005, ASMT-006). Integrity flags show their times; reviewing them is ASMT-003.
