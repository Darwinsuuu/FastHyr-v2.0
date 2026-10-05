"""The interview link page (INTV-002, SCREEN_SPECS.md S-01): which state a candidate opening
`{SITE_URL}/interview/{token}` sees. Anyone holding the link may learn that it expired or closed,
which says nothing about them; everything personal waits until the signed-in Google or Microsoft
account is the one that applied (ADR-014)."""

import hmac
import math
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_days import format_local, zone_of
from app.core.context import CandidateContext
from app.core.errors import (
    BiometricConsentRequiredError,
    InterviewNotFoundError,
    InterviewNotOpenError,
)
from app.core.tokens import hash_token
from app.interview.plan import INTERVIEW_MINUTES
from app.repositories.company_profiles import BrandingRow
from app.repositories.interviews import InterviewLinkRow, interview_link_of
from app.schemas.interviews import (
    InterviewCompany,
    InterviewConsent,
    InterviewConsentRequest,
    InterviewLink,
    InterviewLinkState,
)
from app.services import consents
from app.services.company_profile import branding_url
from app.services.workspaces import mask_email

# Tokens are `secrets.token_urlsafe(32)` (43 characters); anything far off is not a link of ours.
MAX_TOKEN_LENGTH = 128

# Stages after the interview: the candidate has finished, whatever the outcome.
AFTER_INTERVIEW = frozenset({"scoring", "ready_for_review", "did_not_pass", "advanced"})
# Stages that close the interview step before it is done.
CLOSED_STAGES = frozenset({"rejected", "resume_not_match"})
# States from which the candidate can go through the device check and start (or carry on).
OPEN_STATES = frozenset({"welcome", "resume", "technical_problem"})


async def interview_link(
    session: AsyncSession,
    token: str,
    candidate: CandidateContext | None,
    *,
    api_url: str,
    now: datetime | None = None,
) -> InterviewLink:
    """The link's state for whoever opened it (`candidate` is None when signed out, or signed in
    some other way than Google or Microsoft). `404 interview_not_found` for unknown tokens."""
    row = await link_row(session, token)
    state = resolve(row, candidate, now or datetime.now(UTC))
    interview = row.interview
    personal = state not in ("unavailable", "expired", "sign_in", "wrong_account")
    talk = interview.talk_seconds or 0
    return InterviewLink(
        state=state,
        company=_company(row, api_url),
        job_title=row.job_title or "",
        format="voice_only" if interview.format == "voice_only" else "video_voice",
        expires_at=interview.expires_at,
        expires_label=format_local(interview.expires_at, zone_of(row.timezone)),
        first_name=_first_name(row.candidate_full_name) if personal else None,
        masked_email=mask_email(row.candidate_email) if state == "sign_in" else None,
        minutes_left=(
            max(1, math.ceil((INTERVIEW_MINUTES * 60 - talk) / 60)) if state == "resume" else None
        ),
        face_check=face_check(row),
    )


async def record_consent(
    session: AsyncSession,
    token: str,
    candidate: CandidateContext,
    body: InterviewConsentRequest,
    *,
    now: datetime | None = None,
) -> InterviewConsent:
    """Stores the device check's consent on the interview (INTV-003, PRIVACY.md §3): the
    interview notice, and the biometric notice when the interview runs the face check. Agreeing
    again (resuming, another try) keeps the latest agreement. Another account learns nothing
    about the link (`404`); a link that can't start is `409 interview_not_open`."""
    now = now or datetime.now(UTC)
    row = await link_row(session, token)
    state = resolve(row, candidate, now)
    if state == "wrong_account":
        raise InterviewNotFoundError()
    if state not in OPEN_STATES:
        raise InterviewNotOpenError()

    consent = consents.accept("interview", body.consent_notice_id, now=now)
    biometric = None
    if face_check(row):
        if body.biometric_notice_id is None:
            raise BiometricConsentRequiredError()
        biometric = consents.accept("biometric", body.biometric_notice_id, now=now).notice_id

    interview = row.interview
    interview.consent_version = consent.notice_id
    interview.consent_at = consent.at
    interview.biometric_consent_version = biometric
    await session.commit()
    return InterviewConsent(
        consent_version=consent.notice_id,
        consent_at=consent.at,
        biometric_consent_version=biometric,
    )


def face_check(row: InterviewLinkRow) -> bool:
    """The same-face check runs only on video interviews with integrity checks on (ADR-016)."""
    return row.interview.format != "voice_only" and row.integrity_enabled


async def link_row(session: AsyncSession, token: str) -> InterviewLinkRow:
    """The interview a link token names, with what the page needs. `404 interview_not_found` for
    unknown tokens."""
    if not token or len(token) > MAX_TOKEN_LENGTH:
        raise InterviewNotFoundError()
    token_hash = hash_token(token)
    row = await interview_link_of(session, token_hash)
    # The lookup is an equality match on the hash, so timing reveals nothing about the token;
    # compare again in constant time so a row only ever matches its own hash.
    if row is None or not hmac.compare_digest(row.interview.token_hash, token_hash):
        raise InterviewNotFoundError()
    return row


def resolve(
    row: InterviewLinkRow, candidate: CandidateContext | None, now: datetime
) -> InterviewLinkState:
    """S-01's state, checked in this order. A finished interview stays "completed": it never
    turns expired or unavailable afterwards."""
    interview = row.interview
    done = interview.status == "completed" or row.application_stage in AFTER_INTERVIEW
    if not done and (
        interview.superseded_by is not None
        or row.candidate_deleted_at is not None
        or row.pipeline_status == "cancelled"
        or row.application_stage in CLOSED_STAGES
    ):
        return "unavailable"
    if not done and (interview.status == "expired" or interview.expires_at <= now):
        return "expired"
    if candidate is None:
        return "sign_in"
    if candidate.user_id != row.candidate_auth_user_id:
        return "wrong_account"
    if done:
        return "completed"
    if interview.drop_reason == "technical_issue":
        return "technical_problem"
    if interview.status in ("in_progress", "abandoned"):
        return "resume"
    return "welcome"


def _company(row: InterviewLinkRow, api_url: str) -> InterviewCompany:
    # The same long-lived logo link the apply page and emails use.
    branding = BrandingRow(row.company_name, row.logo_path, None, row.profile_updated_at)
    return InterviewCompany(
        name=row.company_name,
        logo_url=(
            branding_url(api_url, row.interview.workspace_id, branding, "logo")
            if row.logo_path
            else None
        ),
        website=row.website,
        careers_url=row.careers_url,
    )


def _first_name(full_name: str) -> str:
    parts = full_name.split()
    return parts[0] if parts else ""
