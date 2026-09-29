"""Departments (API.md "Workspace admin"): any member reads, Admins write."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, status

from app.api.deps import Session, require
from app.core.context import RequestContext
from app.core.errors import PROBLEM_JSON, PROBLEM_RESPONSES, Problem
from app.core.permissions import Action
from app.schemas.departments import (
    CreateDepartmentRequest,
    Department,
    DepartmentList,
    UpdateDepartmentRequest,
)
from app.services import departments as department_service

router = APIRouter(prefix="/departments", tags=["departments"], responses=PROBLEM_RESPONSES)

CONFLICT: dict[int | str, dict[str, Any]] = {409: {"model": Problem, "content": {PROBLEM_JSON: {}}}}

Viewer = Annotated[RequestContext, require(Action.VIEW_DEPARTMENTS)]
Admin = Annotated[RequestContext, require(Action.MANAGE_WORKSPACE)]


@router.get("", response_model=DepartmentList)
async def list_departments(ctx: Viewer, session: Session) -> DepartmentList:
    """Admins also get pipeline counts and who can see each department, plus No department."""
    return await department_service.list_departments(session, ctx)


@router.post("", response_model=Department, status_code=status.HTTP_201_CREATED, responses=CONFLICT)
async def create_department(
    body: CreateDepartmentRequest, ctx: Admin, session: Session
) -> Department:
    return await department_service.create_department(session, ctx, body)


@router.patch("/{department_id}", response_model=Department, responses=CONFLICT)
async def update_department(
    department_id: uuid.UUID, body: UpdateDepartmentRequest, ctx: Admin, session: Session
) -> Department:
    return await department_service.update_department(session, ctx, department_id, body)


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(department_id: uuid.UUID, ctx: Admin, session: Session) -> None:
    """Its pipelines move to No department and members lose access through it."""
    await department_service.delete_department(session, ctx, department_id)
