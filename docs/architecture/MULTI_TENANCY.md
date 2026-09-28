# Multi-tenancy

FastHyr is multi-tenant SaaS. The **workspace** is the tenant (ADR-005). A leak between workspaces is the worst bug we can ship; treat these rules as non-negotiable.

## 1. Data ownership
- Every business table has `workspace_id uuid not null references workspaces(id)`, except: `profiles` (per user), `demo_sessions` (no tenant), `contact_requests` (marketing), `stripe_events` (global webhook log), `ai_calls` for demo (nullable workspace).
- Child rows repeat `workspace_id` even when reachable through a parent (e.g. `assessments.workspace_id`), so every query can filter directly and indexes start with `workspace_id`.
- Composite foreign keys `(workspace_id, id)` are used between tenant tables so a row can never point to a parent in another workspace.

## 2. Request context
For every TA request:
1. Verify the Supabase JWT → `user_id`.
2. Read `X-Workspace-Id` → load the membership `(workspace_id, user_id, status='active')`; none → `403 not_a_member`.
3. Build `RequestContext(user_id, workspace_id, role, is_owner, visible_department_ids)`:
   - Admin → all departments **and** No department.
   - Recruiter / Hiring manager → their assigned departments only (No department is invisible to them).
4. Every repository call receives `ctx`; repositories add `WHERE workspace_id = :ws` and, for pipeline-scoped data, `AND (pipeline.department_id = ANY(:depts)` or admin rule`)`.
5. Hiring managers additionally only see applications in stages `ready_for_review`, `advanced` or with the Flagged overlay (`SECURITY.md`).

Candidate requests use a **candidate context**: `user_id` → the candidate's own applications/interviews only (matched on `candidates.auth_user_id`). Public requests (apply page) use a **public context** that can read only published pipeline fields and company profile fields meant for candidates.

Jobs use a **system context** bound to the workspace of the entity being processed.

## 3. Defence in depth
- RLS enabled on every table, with **no** policies for `anon`/`authenticated` roles → the public Supabase keys can't read business data (ADR-006).
- The API's DB role, `fasthyr_api`, is not `postgres`/superuser; it has only table privileges (read and insert only on append-only tables) and bypasses RLS. Default privileges give it every new table and give `anon`/`authenticated` nothing, so later migrations only need `enable row level security`.
- Storage paths start with `{workspace_id}/…`; signed URLs are issued only after the same permission check as the metadata.
- Ava retrieval tools take the `RequestContext` and can only query through the same repositories.
- Caches (TanStack Query on web, any Redis caches on API) are keyed by workspace; switching workspace clears the web cache.

## 4. Testing
- `tests/tenancy/` has a fixture (`tenancy`, in `tests/tenancy/harness.py`) with two workspaces (A, B) and members of each role, signed in through Supabase Auth. For **every** endpoint, a parametrised test asserts that a member of A gets `404` (not `403`, to avoid leaking existence) for B's resources and never sees B's rows in lists or aggregates.
- A CI check fails if a new router endpoint has no tenancy test entry.
- Department-scope tests: a recruiter in Engineering cannot see Sales pipelines, candidates only in Sales pipelines, or No-department pipelines.

## 5. Cross-workspace things that are allowed
- A user's list of workspaces (`GET /me/workspaces`).
- The same person applying to two workspaces creates two separate `candidates` rows; no data is shared between them.
