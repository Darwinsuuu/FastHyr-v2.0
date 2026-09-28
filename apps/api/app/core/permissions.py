"""The permission matrix from SECURITY.md §2, in one place.

`can()` answers whether a role may take an action and how widely. Department and stage limits are
applied by repositories from the `RequestContext`; routers only call `require(action)`.
`apps/web/lib/permissions.ts` mirrors this table for the UI only.
"""

from enum import StrEnum

from app.core.context import RequestContext, Role


class Action(StrEnum):
    VIEW_OVERVIEW = "view_overview"  # Getting started / Overview
    VIEW_PIPELINES = "view_pipelines"  # list, dashboard, setup
    EDIT_PIPELINES = "edit_pipelines"  # create, edit draft, publish, duplicate
    CHANGE_PIPELINE_STATUS = "change_pipeline_status"  # pause, resume, close, cancel, archive
    TOP_UP_PIPELINE = "top_up_pipeline"  # from free credits
    VIEW_CANDIDATES = "view_candidates"  # candidates in a pipeline
    VIEW_CANDIDATE_PROFILE = "view_candidate_profile"  # profile, recording, transcript, downloads
    DECIDE_CANDIDATES = "decide_candidates"  # reject, advance, invite manually, re-invite
    RESOLVE_REVIEWS = "resolve_reviews"  # integrity flags, human-review requests
    VIEW_CANDIDATE_POOL = "view_candidate_pool"
    ASK_AVA = "ask_ava"
    MANAGE_EMAIL_TEMPLATES = "manage_email_templates"  # view and edit
    VIEW_DEPARTMENTS = "view_departments"
    MANAGE_WORKSPACE = "manage_workspace"  # company profile, departments, members, invites
    MANAGE_BILLING = "manage_billing"  # billing, invoices, buy credits, change plan
    VIEW_CREDIT_USAGE = "view_credit_usage"
    DELETE_CANDIDATE_DATA = "delete_candidate_data"


class Access(StrEnum):
    WORKSPACE = "workspace"  # the whole workspace, including "No department"
    DEPARTMENTS = "departments"  # only the member's departments
    SHORTLIST = "shortlist"  # the member's departments, shortlisted candidates only


A, D, S = Access.WORKSPACE, Access.DEPARTMENTS, Access.SHORTLIST

MATRIX: dict[Action, dict[Role, Access]] = {
    Action.VIEW_OVERVIEW: {Role.ADMIN: A, Role.RECRUITER: D, Role.HIRING_MANAGER: S},
    Action.VIEW_PIPELINES: {Role.ADMIN: A, Role.RECRUITER: D, Role.HIRING_MANAGER: D},
    Action.EDIT_PIPELINES: {Role.ADMIN: A, Role.RECRUITER: D},
    Action.CHANGE_PIPELINE_STATUS: {Role.ADMIN: A, Role.RECRUITER: D},
    Action.TOP_UP_PIPELINE: {Role.ADMIN: A, Role.RECRUITER: D},
    Action.VIEW_CANDIDATES: {Role.ADMIN: A, Role.RECRUITER: D, Role.HIRING_MANAGER: S},
    Action.VIEW_CANDIDATE_PROFILE: {Role.ADMIN: A, Role.RECRUITER: D, Role.HIRING_MANAGER: S},
    Action.DECIDE_CANDIDATES: {Role.ADMIN: A, Role.RECRUITER: D},
    Action.RESOLVE_REVIEWS: {Role.ADMIN: A, Role.RECRUITER: D},
    Action.VIEW_CANDIDATE_POOL: {Role.ADMIN: A, Role.RECRUITER: D, Role.HIRING_MANAGER: S},
    Action.ASK_AVA: {Role.ADMIN: A, Role.RECRUITER: D, Role.HIRING_MANAGER: S},
    Action.MANAGE_EMAIL_TEMPLATES: {Role.ADMIN: A, Role.RECRUITER: A},
    Action.VIEW_DEPARTMENTS: {Role.ADMIN: A, Role.RECRUITER: A, Role.HIRING_MANAGER: A},
    Action.MANAGE_WORKSPACE: {Role.ADMIN: A},
    Action.MANAGE_BILLING: {Role.ADMIN: A},
    Action.VIEW_CREDIT_USAGE: {Role.ADMIN: A, Role.RECRUITER: A},
    Action.DELETE_CANDIDATE_DATA: {Role.ADMIN: A},
}


def can(ctx: RequestContext, action: Action) -> Access | None:
    """How widely `ctx` may take `action`, or None when its role may not take it at all."""
    return MATRIX[action].get(ctx.role)
