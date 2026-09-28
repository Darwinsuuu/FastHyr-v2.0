# Frontend (`apps/web`)

## 1. Hosts and routing
One Next.js app serves two hosts. `middleware.ts` rewrites by host:
- `fasthyr.com` → route group `(site)` (marketing, apply, interview, demo, auth).
- `app.fasthyr.com` → route group `(app)` (TA app). Unauthenticated requests redirect to `fasthyr.com/login`.
Locally: `localhost:3000` (site) and `app.localhost:3000` (app).

### Route map
| Route | Screen (frame / spec) | Auth |
|---|---|---|
| `/` | Main landing | public |
| `/employers` | Talent acquisition landing | public |
| `/candidates` | For candidates (marketing only, ADR-018) | public |
| `/pricing` | Spec S-07 | public |
| `/terms`, `/privacy`, `/ai-in-hiring` | Spec S-08 | public |
| `/demo`, `/demo/check`, `/demo/interview` | Demo, DemoDeviceCheck, DemoInterview | public (demo session cookie) |
| `/login` | EmployerLogin | public |
| `/reset-password` | Spec S-05 | recovery session |
| `/verify-email` | Spec S-06 | signed in |
| `/auth/callback` | OAuth/email callback handler | — |
| `/workspaces` | WorkspaceSelect | TA signed in |
| `/join/[code]` | Spec S-04 | TA signed in |
| `/apply/[workspaceSlug]/[pipelineSlug]` | Apply | public; candidate sign-in to apply |
| `/interview/[token]` | Spec S-01/S-02 → device check → live interview | candidate signed in |
| `/review-request/[token]` | Spec S-03 | public (token) |
| app `/getting-started` | GettingStarted | member |
| app `/overview` | Overview | member |
| app `/pipelines` | PipelinesV2 | member |
| app `/pipelines/new`, `/pipelines/[id]/edit` | NewPipeline | Admin, Recruiter |
| app `/pipelines/[id]` (`?tab=dashboard\|candidates\|ava\|setup`) | PipelineView | member (scoped) |
| app `/candidates` (`?tab=dashboard\|list\|ava`) | CandidatePool | member (scoped) |
| app `/candidates/[candidateId]?application=[id]&tab=overview\|resume\|interview` | CandidateProfile | member (scoped) |
| app `/billing` | BillingInvoices | Admin |
| app `/billing/usage` | CreditUsage | Admin, Recruiter (read) |
| app `/settings/company` | CompanyProfile | Admin |
| app `/settings/departments` | Departments | Admin |
| app `/settings/members` | ManageMembers | Admin |
| app `/settings/email-templates`, `/settings/email-templates/[key]` | EmailTemplates, EditEmailTemplate | Admin, Recruiter |

Rules:
- **No names, emails or other personal data in URLs** — IDs (UUIDs) only. (The design's `candidates/bea-garcia` is illustrative.)
- The active workspace is stored in a cookie (`fh_ws`) and sent to the API as the `X-Workspace-Id` header; switching workspace replaces the cookie and resets the query cache.

## 2. Folder structure
```
apps/web/
├── app/
│   ├── (site)/…                 # public + candidate routes
│   ├── (app)/…                  # TA app routes, shared AppShell layout
│   └── api/                     # route handlers only for auth callback / health (no business logic)
├── components/
│   ├── ui/                      # design-system primitives (Button, Input, Select, Dialog, Menu, Tabs, Table, Badge, Signal, Stepper, Toast, JobProgressDialog…)
│   ├── app-shell/               # sidebar, workspace switcher, user menu, account modal
│   ├── charts/                  # Funnel, FlowBar, WeeklyBars, Histogram, Radar, Sparkline
│   └── <feature>/               # pipelines/, candidates/, interview/, billing/, settings/, marketing/
├── lib/
│   ├── api/                     # client from packages/api-client + query keys
│   ├── supabase/                # browser/server clients (auth only)
│   ├── interview/               # WebRTC + OpenAI Realtime client, recorder, uploader, device checks
│   ├── format/                  # dates, numbers, money (locale + workspace time zone)
│   └── permissions.ts           # UI gating mirrors API permissions (never the only check)
├── messages/en.json             # all UI copy (NFR-12)
└── styles/tokens.css            # generated from docs/design/tokens.json
```

## 3. Conventions
- **Server vs client components:** pages are server components that render layout and static copy; data that changes (lists, dashboards) is fetched client-side with TanStack Query so polling and optimistic updates are simple. Marketing pages are fully static.
- **API calls** only through the generated client; never `fetch` business endpoints by hand. Query keys are defined in `lib/api/keys.ts`.
- **Polling:** application stages and job progress poll every 3–5 s while something is processing; stop when idle.
- **Forms:** React Hook Form + Zod schemas that mirror API validation; show the API's field errors verbatim.
- **Long jobs (PDFs):** `JobProgressDialog` implements the design's "Please don't close or refresh this window" pattern by polling `GET /jobs/{id}`.
- **Copy:** from `messages/en.json`, sentence case, follow `design/VOICE_AND_TONE.md`.
- **Mobile first:** write base styles for a 360 px phone and add `sm:`…`2xl:` overrides; follow the pattern table in `design/RESPONSIVE.md` (tables → cards, sidebar → drawer, dialogs → sheets). Use `useMediaQuery` only when markup must differ, not for styling.
- **Two sides:** TA screens use `side="ta"` (evergreen) components; candidate screens use `side="candidate"` (persimmon) and at most one primary action.
- **Accessibility:** real buttons/links/inputs with labels, focus ring token, `aria-*` on icon-only buttons, reduced-motion support, keyboard-operable menus and dialogs (Radix).
- **Empty, loading and error states** for every list and card (skeletons, not spinners, for TA tables).
- **Feature flags:** none in MVP; unfinished screens are simply not linked.

## 4. Interview client (`lib/interview/`)
- `devices.ts` — permissions, camera/mic selection, level meter, face-in-frame + wave detection (on-device, e.g. MediaPipe Face Detection; no frames leave the browser for the check).
- `realtime.ts` — WebRTC peer connection to OpenAI Realtime using the client secret from the API; data channel for events (captions, speaking state, topic updates via tool calls).
- `recorder.ts` — `MediaRecorder` on a composed stream (camera video + mixed candidate/AI audio), 10-second timeslices.
- `uploader.ts` — uploads each chunk to its pre-signed URL with retry; reports progress; requests more URLs when running low.
- `session.ts` — state machine (checking → ready → connecting → live → wrapping_up → uploading → done / error), heartbeat, reconnect, resume.
Details in `MEDIA.md`.
