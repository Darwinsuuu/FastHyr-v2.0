"""The permission matrix matches SECURITY.md §2 for every action and role.

The expected table is written out by hand from SECURITY.md so a change to `MATRIX` has to be a
deliberate change here too.
"""

import uuid

import pytest

from app.core.context import RequestContext, Role
from app.core.permissions import MATRIX, Access, Action, can

A, D, S, NO = Access.WORKSPACE, Access.DEPARTMENTS, Access.SHORTLIST, None

#                                   Admin  Recruiter  Hiring manager
EXPECTED: dict[Action, tuple[Access | None, Access | None, Access | None]] = {
    Action.VIEW_OVERVIEW:           (A, D, S),
    Action.VIEW_PIPELINES:          (A, D, D),
    Action.EDIT_PIPELINES:          (A, D, NO),
    Action.CHANGE_PIPELINE_STATUS:  (A, D, NO),
    Action.TOP_UP_PIPELINE:         (A, D, NO),
    Action.VIEW_CANDIDATES:         (A, D, S),
    Action.VIEW_CANDIDATE_PROFILE:  (A, D, S),
    Action.DECIDE_CANDIDATES:       (A, D, NO),
    Action.RESOLVE_REVIEWS:         (A, D, NO),
    Action.VIEW_CANDIDATE_POOL:     (A, D, S),
    Action.ASK_AVA:                 (A, D, S),
    Action.MANAGE_EMAIL_TEMPLATES:  (A, A, NO),
    Action.VIEW_DEPARTMENTS:        (A, A, A),
    Action.MANAGE_WORKSPACE:        (A, NO, NO),
    Action.MANAGE_BILLING:          (A, NO, NO),
    Action.VIEW_CREDIT_USAGE:       (A, A, NO),
    Action.DELETE_CANDIDATE_DATA:   (A, NO, NO),
}  # fmt: skip

ROLES = (Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER)


def context(role: Role) -> RequestContext:
    return RequestContext(
        user_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        member_id=uuid.uuid4(),
        role=role,
        is_owner=False,
    )


def test_every_action_is_in_the_matrix() -> None:
    assert set(EXPECTED) == set(Action) == set(MATRIX)


@pytest.mark.parametrize("action", list(Action))
@pytest.mark.parametrize("role_index", range(3), ids=[r.value for r in ROLES])
def test_can(action: Action, role_index: int) -> None:
    assert can(context(ROLES[role_index]), action) == EXPECTED[action][role_index]


def test_only_admins_see_all_departments() -> None:
    assert context(Role.ADMIN).sees_all_departments
    assert not context(Role.RECRUITER).sees_all_departments
    assert not context(Role.HIRING_MANAGER).sees_all_departments
