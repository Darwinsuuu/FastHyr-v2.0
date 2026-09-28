# ADR-005: Workspace tenancy, departments and three roles

- **Status:** Accepted
- **Date:** 2026-09-29

## Decision
- The **workspace** is the tenant. Every business row carries `workspace_id`. A user can belong to several workspaces and switches between them.
- **Departments** group pipelines inside a workspace. A pipeline has zero or one department; "No department" means `department_id IS NULL` and is visible to admins only.
- **Roles** (per membership):
  - **Admin** — everything, including billing, members, company profile, departments and all pipelines.
  - **Recruiter** — creates, edits and runs pipelines in their departments; reviews, rejects and advances candidates there; edits email templates; can top up a pipeline's credits from free credits.
  - **Hiring manager** — read-only access to *shortlisted* candidates (Ready for review, Flagged, Advanced) and their assessments in their departments; can download reports and use Ava within that scope. Cannot edit pipelines or change candidate status in MVP.
- The workspace creator is the **owner** (an Admin who cannot be removed).
- **Candidates** are not workspace members. A candidate record is per workspace (the "candidate pool") and links to the person's Supabase user.

## Consequences
- Every API query goes through a workspace-scoped repository layer and a permission check (see `architecture/MULTI_TENANCY.md`).
- Ava must apply the same department scope as the member asking.
- The full permission matrix lives in `architecture/SECURITY.md`.
