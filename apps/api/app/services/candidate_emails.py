"""Scheduling candidate emails (MSG-003, NOTIFICATIONS.md §1, FR-MSG-04/05).

`schedule()` renders the workspace's template for one application and stores it with the stage
the application is in, to be sent at `at` (now when not given). Callers decide whether the email
goes out at all (the pipeline's toggles) and pass the values only they know: `Interview.link`
and `Interview.expiry` for the interview emails, `Review.link` for rejections. Use
`send_at()` for a business-day delay in the workspace time zone.

An email never contradicts the candidate's status: `applications.move_stage()` cancels the
application's waiting emails, and the send job cancels one whose application has moved on from
the stage it was written for. Scheduling is idempotent per template, application and stage, so a
retried job never schedules a second copy.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_days import add_business_days, format_local, zone_of
from app.core.config import Settings
from app.core.errors import NotFoundError
from app.emails.candidate import render_template
from app.emails.defaults import TemplateKey
from app.models import EmailMessage
from app.repositories.applications import ApplicationRepository, EmailRecipient
from app.repositories.company_profiles import workspace_timezone
from app.services import company_profile, email_templates
from app.services.emails import queue_unique_email, via_fasthyr


@dataclass(frozen=True)
class ScheduledEmail:
    message: EmailMessage
    # False when the same email was already scheduled (a retried job).
    created: bool


def names(full_name: str) -> tuple[str, str]:
    """First and last name for `[Candidate.firstname]` / `[Candidate.lastname]`: the first and the
    last word of the name the candidate gave (one word fills both)."""
    words = full_name.split()
    if not words:
        return "", ""
    return words[0], words[-1]


async def send_at(
    session: AsyncSession, workspace_id: uuid.UUID, start: datetime, business_days: int
) -> datetime:
    """`business_days` business days after `start` in the workspace's time zone."""
    timezone = await workspace_timezone(session, workspace_id)
    return add_business_days(start, business_days, zone_of(timezone))


async def local_time(session: AsyncSession, workspace_id: uuid.UUID, moment: datetime) -> str:
    """A time written for the workspace's candidates, e.g. for `Interview.expiry`."""
    return format_local(moment, zone_of(await workspace_timezone(session, workspace_id)))


async def schedule(
    session: AsyncSession,
    settings: Settings,
    *,
    workspace_id: uuid.UUID,
    application_id: uuid.UUID,
    key: TemplateKey,
    at: datetime | None = None,
    values: dict[str, str] | None = None,
    dedupe_key: str | None = None,
) -> ScheduledEmail:
    """Renders and stores the email in the caller's transaction; the caller commits, then calls
    `emails.enqueue(queue, result.message)` (a no-op for emails due later). `dedupe_key` replaces
    the default `{key}:{application}:{stage}` when an email may rightly go twice in one stage
    (e.g. a re-invite). Raises `MissingParameterError` when the template uses a value nobody
    gave, so a candidate never gets a literal "[Interview.link]"."""
    recipient = await ApplicationRepository(session, workspace_id).email_recipient(application_id)
    if recipient is None:
        raise NotFoundError()
    template = await email_templates.get_template(session, workspace_id, key)
    brand = await company_profile.branding(session, workspace_id, api_url=settings.api_url)
    email = render_template(
        key=key,
        subject=template.subject,
        body_html=template.body_html,
        values={**_values(recipient, brand.company_name), **(values or {})},
        site_url=settings.site_url,
        branding=brand,
    )
    message, created = await queue_unique_email(
        session,
        dedupe_key=dedupe_key or f"{key.value}:{application_id}:{recipient.stage}",
        application_stage=recipient.stage,
        workspace_id=workspace_id,
        application_id=application_id,
        template_key=key.value,
        to_email=recipient.email,
        from_name=via_fasthyr(brand.company_name),
        email=email,
        scheduled_for=at or datetime.now(UTC),
    )
    return ScheduledEmail(message=message, created=created)


def _values(recipient: EmailRecipient, company: str) -> dict[str, str]:
    first, last = names(recipient.full_name)
    return {
        "Candidate.firstname": first,
        "Candidate.lastname": last,
        "Job.title": recipient.job_title,
        "Company.name": company,
    }
