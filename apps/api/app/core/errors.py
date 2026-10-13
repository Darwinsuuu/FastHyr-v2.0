"""Errors as RFC 9457 `application/problem+json` with a stable `code` the web maps to copy.

Bodies never carry personal data: no emails, names or submitted values, only codes and IDs.
"""

import logging
from typing import Any, ClassVar

import sentry_sdk
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

    def __init__(self, title: str | None = None, *, errors: list[dict[str, Any]] | None = None):
        super().__init__(title or self.title)
        self.detail_title = title or self.title
        # Which fields are wrong, as `{loc, type, msg}` like validation errors; never values.
        self.errors = errors


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


class CandidateSignInRequiredError(AppError):
    """Candidate routes need a Google or Microsoft sign-in (ADR-014)."""

    status = 403
    code = "candidate_sign_in_required"
    title = "Sign in with Google or Microsoft to apply"


class NotFoundError(AppError):
    """Also used for resources outside the caller's workspace or scope, so they stay invisible."""

    status = 404
    code = "not_found"
    title = "Not found"


class InterviewNotFoundError(AppError):
    status = 404
    code = "interview_not_found"
    title = "We couldn't find that interview"


class DecisionNotAllowedError(AppError):
    """The candidate can't be advanced or rejected from the stage they're in: advancing needs
    Ready for review, rejecting a stage before a decision, and both are final (ASMT-007)."""

    status = 409
    code = "decision_not_allowed"
    title = "This candidate can't be moved from their current stage"


class FlagsToReviewError(AppError):
    """Advance waits until every integrity flag on the interview is reviewed (A-02, ASMT-003)."""

    status = 409
    code = "flags_to_review"
    title = "Review this candidate's integrity flags first"


class ReinviteNotAllowedError(AppError):
    """The application can't get a new interview link: it isn't waiting on its interview, the
    interview is finished or running right now, or the pipeline is cancelled (INTV-007)."""

    status = 409
    code = "reinvite_not_allowed"
    title = "This candidate can't be re-invited"


class InterviewNotOpenError(AppError):
    """The interview link has expired, closed or finished, so it can't be started (INTV-003)."""

    status = 409
    code = "interview_not_open"
    title = "This interview can't be started"


class InterviewConsentRequiredError(AppError):
    """The session starts only after the device check's consent is recorded (INTV-003)."""

    status = 409
    code = "interview_consent_required"
    title = "Agree to the interview notice first"


class InterviewTechnicalIssueError(AppError):
    """Three connections failed within 5 minutes (MEDIA.md §2): the link stays valid and the
    page shows "We couldn't connect you"."""

    status = 409
    code = "interview_technical_issue"
    title = "We couldn't connect you"


class InterviewAttemptNotFoundError(AppError):
    status = 404
    code = "interview_attempt_not_found"
    title = "We couldn't find that interview session"


class RecordingChunkMissingError(AppError):
    """A recording chunk was registered before (or without) its upload (INTV-006)."""

    status = 422
    code = "recording_chunk_missing"
    title = "That part of the recording hasn't arrived"


class RecordingChunkTooLargeError(AppError):
    status = 422
    code = "recording_chunk_too_large"
    title = "That part of the recording is too large"


class RecordingTypeMismatchError(AppError):
    """An attempt records one stream: its chunks can't switch between WebM and MP4."""

    status = 409
    code = "recording_type_mismatch"
    title = "That recording format doesn't match this session"


class RecordingFinalizedError(AppError):
    """The interview's recording is already being put together; later chunks can't join it."""

    status = 409
    code = "recording_finalized"
    title = "This recording is already saved"


class RealtimeUnavailableAppError(AppError):
    status = 503
    code = "realtime_unavailable"
    title = "The interviewer can't be reached right now"


class RealtimeOfferRejectedAppError(AppError):
    status = 422
    code = "realtime_offer_rejected"
    title = "Your browser's connection details were refused"


class BiometricConsentRequiredError(AppError):
    """A video interview with integrity checks needs the face-check consent too (ADR-016)."""

    status = 422
    code = "biometric_consent_required"
    title = "Agree to the face check to start this interview"


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


class InsufficientFreeCreditsError(AppError):
    """Reserving or topping up more than the workspace's free credits (FR-BILL-04)."""

    status = 409
    code = "insufficient_free_credits"
    title = "Not enough free credits"


class PipelineNotAcceptingError(AppError):
    """The pipeline isn't live, its reserve is used up, or the workspace has no credits left.
    No credit is used (BILLING.md §4)."""

    status = 409
    code = "pipeline_not_accepting"
    title = "This pipeline isn't accepting applications"


class InvalidTransitionError(AppError):
    """The pipeline's status doesn't allow this action (WORKFLOW.md §2)."""

    status = 409
    code = "invalid_transition"
    title = "This pipeline can't do that right now"


class PipelineLockedError(AppError):
    """The setup of a pipeline that has opened can't change (WORKFLOW.md §2 lock rule)."""

    status = 409
    code = "pipeline_locked"
    title = "This pipeline's setup is locked"


class PipelineIncompleteError(AppError):
    """Publishing a draft whose setup is missing something; `errors` names the fields."""

    status = 422
    code = "pipeline_incomplete"
    title = "Finish the pipeline setup first"


class DepartmentNameTakenError(AppError):
    """Department names are unique per workspace, ignoring case (FR-WS-02)."""

    status = 409
    code = "department_name_taken"
    title = "A department with this name already exists"


class DepartmentNameReservedError(AppError):
    """The name "No department" is built in (FR-WS-02)."""

    status = 422
    code = "department_name_reserved"
    title = "This name is reserved"


class OwnerAccessLockedError(AppError):
    """The workspace owner is always an Admin and can't be removed (FR-WS-04)."""

    status = 409
    code = "owner_access_locked"
    title = "The workspace owner's access can't be changed"


class OwnAccessLockedError(AppError):
    """Admins can't change or remove their own access, so nobody locks themselves out."""

    status = 409
    code = "own_access_locked"
    title = "You can't change your own access"


class UnknownDepartmentError(AppError):
    status = 422
    code = "unknown_department"
    title = "Choose departments from this workspace"


class AlreadyAMemberError(AppError):
    """The email belongs to someone who already has access to this workspace (FR-WS-03)."""

    status = 409
    code = "already_a_member"
    title = "This person is already a member"


class PdfInvalidError(AppError):
    """Base for a résumé or other PDF that failed the checks in services/pdfs.py (STORAGE.md)."""

    status = 422
    code = "pdf_invalid"
    title = "This file can't be used"


class PdfNotPdfError(PdfInvalidError):
    code = "pdf_not_pdf"
    title = "Upload a PDF file"


class PdfTooLargeError(PdfInvalidError):
    code = "pdf_too_large"
    title = "This PDF is larger than 10 MB"


class PdfMalformedError(PdfInvalidError):
    code = "pdf_malformed"
    title = "This PDF is damaged and can't be opened"


class PdfEncryptedError(PdfInvalidError):
    code = "pdf_encrypted"
    title = "This PDF is password-protected"


class PdfTooManyPagesError(PdfInvalidError):
    code = "pdf_too_many_pages"
    title = "This PDF has more than 20 pages"


class UploadMissingError(AppError):
    """The browser never finished uploading to its signed URL, or the file was already used."""

    status = 422
    code = "upload_missing"
    title = "We didn't receive the file. Upload it again."


class UploadExpiredError(AppError):
    """The file arrived after its upload URL's 10-minute window (STORAGE.md)."""

    status = 410
    code = "upload_expired"
    title = "The upload took too long. Upload the file again."


class ImageInvalidError(AppError):
    """Base for a logo or banner that failed the checks in services/images.py (FR-WS-01)."""

    status = 422
    code = "image_invalid"
    title = "This image can't be used. Upload a PNG or JPG file."


class ImageTooLargeError(ImageInvalidError):
    code = "image_too_large"
    title = "This image is larger than 2 MB"


class ImageDimensionsTooLargeError(ImageInvalidError):
    code = "image_too_big"
    title = "This image is more than 4096 pixels wide or tall"


class LogoNotSquareError(ImageInvalidError):
    code = "logo_not_square"
    title = "The logo must be square"


class LogoTooSmallError(ImageInvalidError):
    code = "logo_too_small"
    title = "The logo must be at least 256 pixels wide and tall"


class WorkspaceRequiredError(AppError):
    status = 400
    code = "workspace_required"
    title = "Choose a workspace first"


class InvalidWebhookSignatureError(AppError):
    """A webhook whose signature doesn't match its provider's secret, or is too old (FND-010)."""

    status = 400
    code = "invalid_webhook_signature"
    title = "Webhook signature check failed"


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
    return problem_response(
        request, status=exc.status, code=exc.code, title=exc.detail_title, errors=exc.errors
    )


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
    sentry_sdk.capture_exception(exc)
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


class NoticeUnknownError(AppError):
    """The consent names a notice that was never released, or one of another kind (FR-COMP-01)."""

    status = 422
    code = "notice_unknown"
    title = "This notice isn't one we show"


class NoticeOutdatedError(AppError):
    """The candidate agreed to an older version of a notice; the page shows the current one."""

    status = 409
    code = "notice_outdated"
    title = "This notice has been updated. Read it again and agree to continue."


class EmailTemplateInvalidError(AppError):
    """A template save that would send a broken email (FR-MSG-03): an unknown parameter, or an
    empty or too long subject or message. `errors` names each problem; for unknown parameters
    `msg` is the parameter as written, which is template text, never personal data."""

    status = 422
    code = "email_template_invalid"
    title = "This template can't be saved yet"
