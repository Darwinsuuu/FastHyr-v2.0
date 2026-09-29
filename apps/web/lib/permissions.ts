// The permission matrix from SECURITY.md §2, mirrored from `apps/api/app/core/permissions.py`.
// UI gating only: it hides what a role can't use. The API's `require(action)` is the real check,
// so a hidden page's data is refused whatever the UI does.

export type Role = "admin" | "recruiter" | "hiring_manager";

export type Action =
  | "view_overview"
  | "view_pipelines"
  | "edit_pipelines"
  | "change_pipeline_status"
  | "top_up_pipeline"
  | "view_candidates"
  | "view_candidate_profile"
  | "decide_candidates"
  | "resolve_reviews"
  | "view_candidate_pool"
  | "ask_ava"
  | "manage_email_templates"
  | "view_departments"
  | "manage_workspace"
  | "manage_billing"
  | "view_credit_usage"
  | "delete_candidate_data";

/** How widely a role may act: the whole workspace, its departments, or shortlisted candidates. */
export type Access = "workspace" | "departments" | "shortlist";

const A = "workspace",
  D = "departments",
  S = "shortlist";

export const MATRIX: Record<Action, Partial<Record<Role, Access>>> = {
  view_overview: { admin: A, recruiter: D, hiring_manager: S },
  view_pipelines: { admin: A, recruiter: D, hiring_manager: D },
  edit_pipelines: { admin: A, recruiter: D },
  change_pipeline_status: { admin: A, recruiter: D },
  top_up_pipeline: { admin: A, recruiter: D },
  view_candidates: { admin: A, recruiter: D, hiring_manager: S },
  view_candidate_profile: { admin: A, recruiter: D, hiring_manager: S },
  decide_candidates: { admin: A, recruiter: D },
  resolve_reviews: { admin: A, recruiter: D },
  view_candidate_pool: { admin: A, recruiter: D, hiring_manager: S },
  ask_ava: { admin: A, recruiter: D, hiring_manager: S },
  manage_email_templates: { admin: A, recruiter: A },
  view_departments: { admin: A, recruiter: A, hiring_manager: A },
  manage_workspace: { admin: A },
  manage_billing: { admin: A },
  view_credit_usage: { admin: A, recruiter: A },
  delete_candidate_data: { admin: A },
};

/** How widely `role` may take `action`, or null when it may not at all. */
export function access(role: Role, action: Action): Access | null {
  return MATRIX[action][role] ?? null;
}

export function can(role: Role, action: Action): boolean {
  return access(role, action) !== null;
}
