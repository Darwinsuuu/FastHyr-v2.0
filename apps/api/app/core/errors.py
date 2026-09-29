"""Errors as RFC 9457 `application/problem+json` with a stable `code` the web maps to copy.

Bodies never carry personal data: no emails, names or submitted values, only codes and IDs.
"""

import logging
from typing import Any, ClassVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_of

logger = logging.getLogger(__name__)

PROBLEM_JSON = "application/problem+json"


class Problem(BaseModel):
    """The error body every endpoint returns."""

    type: str
    title: str
    status: int
    code: str
    request_id: str | None = None
    errors: list[dict[str, Any]] | None = None


class AppError(Exception):
    status: ClassVar[int] = 400
    code: ClassVar[str] = "bad_request"
    title: ClassVar[str] = "Bad request"

    def __init__(self, title: str | None = None) -> None:
        super().__init__(title or self.title)
        self.detail_title = title or self.title


class UnauthenticatedError(AppError):
    status = 401
    code = "unauthenticated"
    title = "Sign in to continue"


class NotAMemberError(AppError):
    status = 403
    code = "not_a_member"
    title = "You are not a member of this workspace"


class ForbiddenError(AppError):
    status = 403
    code = "forbidden"
    title = "Your role cannot do this"


class EmailNotVerifiedError(AppError):
    """Email + password accounts verify their email before creating or joining a workspace
    (FR-AUTH-03)."""

    status = 403
    code = "email_not_verified"
    title = "Verify your email first"


class NotFoundError(AppError):
    """Also used for resources outside the caller's workspace or scope, so they stay invisible."""

    status = 404
    code = "not_found"
    title = "Not found"


class InviteNotFoundError(AppError):
    status = 404
    code = "invite_not_found"
    title = "We couldn't find that invite"


class InviteWrongEmailError(AppError):
    """The invite is addressed to a different email than the signed-in one (FR-AUTH-06)."""

    status = 403
    code = "invite_wrong_email"
    title = "This invite was sent to a different email"


class InviteExpiredError(AppError):
    status = 410
    code = "invite_expired"
    title = "This invite has expired"


class InviteInvalidError(AppError):
    """Revoked, or already used by someone else."""

    status = 410
    code = "invite_invalid"
    title = "This invite is no longer valid"


class WorkspaceRequiredError(AppError):
    status = 400
    code = "workspace_required"
    title = "Choose a workspace first"


def problem_response(
    request: Request,
    *,
    status: int,
    code: str,
    title: str,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    request_id = request_id_of(request)
    body = Problem(
        type=f"https://fasthyr.com/errors/{code}",
        title=title,
        status=status,
        code=code,
        request_id=request_id,
        errors=errors,
    )
    headers = {"X-Request-Id": request_id} if request_id else None
    return JSONResponse(
        body.model_dump(exclude_none=True),
        status_code=status,
        media_type=PROBLEM_JSON,
        headers=headers,
    )


_HTTP_CODES = {
    401: ("unauthenticated", "Sign in to continue"),
    403: ("forbidden", "Your role cannot do this"),
    404: ("not_found", "Not found"),
    405: ("method_not_allowed", "Method not allowed"),
}


async def _app_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return problem_response(request, status=exc.status, code=exc.code, title=exc.detail_title)


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code, title = _HTTP_CODES.get(exc.status_code, ("http_error", "Request failed"))
    return problem_response(request, status=exc.status_code, code=code, title=title)


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Keep where and why, never the submitted value (it may be personal data).
    errors = [
        {"loc": list(error.get("loc", ())), "type": error.get("type"), "msg": error.get("msg")}
        for error in exc.errors()
    ]
    return problem_response(
        request, status=422, code="validation_failed", title="Check the fields", errors=errors
    )


async def _unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error", extra={"error_type": type(exc).__name__})
    return problem_response(
        request, status=500, code="internal_error", title="Something went wrong on our side"
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(Exception, _unexpected_error)


PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    status: {"model": Problem, "content": {PROBLEM_JSON: {}}} for status in (401, 403, 404, 422)
}
"""Pass as `responses=` on routers so the OpenAPI schema documents the error shape."""
