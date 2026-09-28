# User stories

Format: **As a** role, **I want** …, **so that** …. Each story lists the requirements it covers and the gap areas (G1–G9) it touches. Acceptance criteria live in the requirements and in each task file.

Roles: **TA** (Recruiter or Admin), **Admin**, **HM** (Hiring manager), **Cand** (Candidate), **Visitor** (public site / demo).

## Epic AUTH — Sign in and workspaces
| ID | Story | Covers | G |
|---|---|---|---|
| US-AUTH-1 | As a TA, I want to sign in with Google, Microsoft or email and password, so that I can use the account I already have. | FR-AUTH-01, 03 | — |
| US-AUTH-2 | As a TA, I want to reset a forgotten password by email, so that I'm never locked out. | FR-AUTH-02 | — |
| US-AUTH-3 | As a new TA, I want to create a workspace for my company, so that I can start hiring with free trial credits. | FR-AUTH-05, FR-BILL-02 | — |
| US-AUTH-4 | As an invited TA, I want to join my team's workspace from the invite link, so that I see the pipelines I'm allowed to. | FR-AUTH-06 | — |
| US-AUTH-5 | As a TA in several companies, I want to switch workspaces, so that I keep their data apart. | FR-AUTH-07 | — |

## Epic WS — Workspace admin
| ID | Story | Covers | G |
|---|---|---|---|
| US-WS-1 | As an Admin, I want to set our logo, banner and company intro, so that candidates recognise us on every page and email. | FR-WS-01 | G5 |
| US-WS-2 | As an Admin, I want to group pipelines into departments, so that people only see their team's roles. | FR-WS-02 | — |
| US-WS-3 | As an Admin, I want to invite recruiters and hiring managers with specific departments, so that access matches responsibility. | FR-WS-03, 04, 05 | — |

## Epic DASH — Getting started and Overview
| ID | Story | Covers | G |
|---|---|---|---|
| US-DASH-1 | As a new Admin, I want a checklist of setup steps, so that my first pipeline runs on its own. | FR-DASH-01 | — |
| US-DASH-2 | As a TA, I want to see what needs me today (reviews, flags, review requests, credit problems), so that nothing waits too long. | FR-DASH-03 | G1, G7 |
| US-DASH-3 | As a TA lead, I want funnel, time-to-screen, source and drop-off numbers, so that I can show the value of FastHyr. | FR-DASH-02, 04 | G8, G1 |

## Epic PIPE — Pipelines
| ID | Story | Covers | G |
|---|---|---|---|
| US-PIPE-1 | As a TA, I want to describe the role, must-haves, nice-to-haves and résumé pass bar, so that screening matches what I need. | FR-PIPE-01 | G2, G4 |
| US-PIPE-2 | As a TA, I want to choose video or voice, tone, seniority and skills to probe, so that the interview fits the role. | FR-PIPE-02 | G3 |
| US-PIPE-3 | As a TA, I want to set rubric weights and a pass mark, so that I decide what a good interview is. | FR-PIPE-03 | G4 |
| US-PIPE-4 | As a TA, I want to schedule the opening and reserve credits, so that busy roles can't starve others. | FR-PIPE-04 | — |
| US-PIPE-5 | As a TA, I want the setup locked after it opens, so that every candidate is assessed the same way. | FR-PIPE-05, 07 | G2, G4 |
| US-PIPE-6 | As a TA, I want tagged apply links per job board, so that I can see which board brings good candidates. | FR-PIPE-10 | G8 |
| US-PIPE-7 | As a TA, I want to pause, resume, close, cancel, archive or duplicate pipelines, so that I control intake. | FR-PIPE-07 | G5 |
| US-PIPE-8 | As a TA, I want a pipeline dashboard with funnel, scores, sources and drop-offs, and to re-invite people who didn't finish, so that I recover lost candidates. | FR-PIPE-11 | G1, G8 |
| US-PIPE-9 | As a TA, I want to filter candidates by stage and act on them (advance, reject with reason, download, email), so that I can move quickly. | FR-PIPE-12, 13 | G5, G6 |
| US-PIPE-10 | As a TA lead, I want a PDF report across pipelines, so that I can share results with leadership. | FR-PIPE-09 | G8 |

## Epic APPLY — Apply
| ID | Story | Covers | G |
|---|---|---|---|
| US-APPLY-1 | As a Cand, I want a clear job page that shows how applying and the AI interview work, so that I know what to expect. | FR-APPLY-01 | G2 |
| US-APPLY-2 | As a Cand, I want to sign in with Google or Microsoft and upload my résumé in a few minutes, so that applying is quick. | FR-APPLY-02, 03, 04 | — |
| US-APPLY-3 | As a Cand, I want to be told plainly if a role isn't taking applications, so that I don't waste time. | FR-APPLY-06 | — |

## Epic SCREEN — Résumé screening
| ID | Story | Covers | G |
|---|---|---|---|
| US-SCREEN-1 | As a TA, I want every résumé read against my must-haves (not keywords) within minutes, so that no one waits in an inbox. | FR-SCREEN-01..06 | G2 |
| US-SCREEN-2 | As a Cand, I want personal details ignored when my résumé is scored, so that I'm judged on my work. | FR-SCREEN-02 | G2 |
| US-SCREEN-3 | As a Cand who wasn't a match, I want a kind message and a way to ask a person to review it, so that I'm not ghosted by a machine. | FR-COMP-03, FR-MSG-01 | G2, G5 |

## Epic INTV — AI interview
| ID | Story | Covers | G |
|---|---|---|---|
| US-INTV-1 | As a Cand, I want to check my camera and mic before starting, so that technical problems don't ruin my interview. | FR-INTV-03 | G1 |
| US-INTV-2 | As a Cand, I want a real conversation about my own work, where I can ask questions about the role, so that I can show what I can do. | FR-INTV-01, 04 | G3 |
| US-INTV-3 | As a Cand, I want to pick up where I left off if I get disconnected, so that I don't lose my chance. | FR-INTV-06 | G1 |
| US-INTV-4 | As a Cand, I want reminders before my link expires, so that I don't miss it. | FR-MSG-01, FR-PIPE-02 | G1 |
| US-INTV-5 | As a Cand, I want to know what happens next when I finish, so that I'm not left wondering. | FR-INTV-07, FR-MSG-01 | G5 |

## Epic ASMT — Assessment and review
| ID | Story | Covers | G |
|---|---|---|---|
| US-ASMT-1 | As a TA, I want to see how a score was calculated and the interview moments behind it, so that I trust and can defend it. | FR-ASMT-02..04, 07 | G4 |
| US-ASMT-2 | As a TA, I want to watch or listen to the interview, jump to topics and search the transcript, so that I can check evidence quickly. | FR-ASMT-01, 07 | — |
| US-ASMT-3 | As a TA, I want possible impersonation flagged at exact moments for me to review, so that integrity is protected without unfair auto-rejections. | FR-ASMT-06 | G7 |
| US-ASMT-4 | As a TA or HM, I want a PDF candidate report, so that I can share it with the hiring team. | FR-ASMT-08 | — |
| US-ASMT-5 | As a HM, I want to see only the shortlisted candidates for my department with their assessments, so that I can decide who to meet. | FR-WS-06 | G6 |
| US-ASMT-6 | As a TA, I want to resolve human-review requests (uphold or override), so that candidates get a real second look. | FR-COMP-03 | G2 |

## Epic CAND / AVA — Candidates pool and Ava
| ID | Story | Covers | G |
|---|---|---|---|
| US-CAND-1 | As a TA, I want to see everyone who has applied to us and their history, so that I can spot strong returning candidates. | FR-CAND-01..04 | G8 |
| US-AVA-1 | As a TA, I want to ask Ava to compare candidates, summarise flags or explain résumé failures, with sources, so that I get answers fast. | FR-AVA-01..05 | G2, G8 |

## Epic MSG — Candidate emails
| ID | Story | Covers | G |
|---|---|---|---|
| US-MSG-1 | As a TA, I want ready-made emails for each step that send themselves at the right time, so that every candidate hears back. | FR-MSG-01, 04, 05 | G5 |
| US-MSG-2 | As a TA, I want to edit the wording with candidate details, test it, and restore old versions, so that emails sound like us. | FR-MSG-02, 03 | G5 |

## Epic BILL — Billing and credits
| ID | Story | Covers | G |
|---|---|---|---|
| US-BILL-1 | As an Admin, I want to choose a plan and pay by card, so that my team can keep hiring. | FR-BILL-01, 06 | — |
| US-BILL-2 | As an Admin, I want to buy extra credits in packs, so that a hiring spike doesn't stop us. | FR-BILL-07 | — |
| US-BILL-3 | As an Admin, I want to see where credits go, what expires when, and which pipelines are running low, so that nothing pauses by surprise. | FR-BILL-03, 04, 08 | G8 |
| US-BILL-4 | As an Admin, I want invoices I can download, so that finance can reconcile. | FR-BILL-05 | — |

## Epic WEB / DEMO — Public site and demo
| ID | Story | Covers | G |
|---|---|---|---|
| US-WEB-1 | As a Visitor, I want to understand what FastHyr does for employers and candidates, see pricing and contact the team, so that I can decide to try it. | FR-WEB-01..04 | — |
| US-DEMO-1 | As a Visitor, I want to take a short AI interview with my own résumé, so that I experience it before sending it to applicants. | FR-DEMO-01..04 | — |

## Epic COMP — Compliance
| ID | Story | Covers | G |
|---|---|---|---|
| US-COMP-1 | As an Admin, I want to delete a candidate's data on request, so that we meet privacy laws. | FR-COMP-05 | — |
| US-COMP-2 | As FastHyr, we want every AI decision logged with model and prompt version, so that we can audit and explain outcomes. | FR-COMP-02 | G2 |
