"""The email send job (NOTIFICATIONS.md): one email_messages row per run."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.email import EmailRejectedError, EmailSender
from app.jobs.framework import JobRun, PermanentJobError, RetryPolicy, job
from app.services import emails as email_service


class EmailRejectedJobError(PermanentJobError):
    code = "provider_rejected"


async def _mark_failed(session: AsyncSession, error: BaseException, args: tuple[Any, ...]) -> None:
    code = getattr(error, "code", None)
    await email_service.record_failure(
        session, args[0], code if isinstance(code, str) else "send_failed"
    )


# Five tries over about two and a half minutes ride out a short provider outage.
@job(retry=RetryPolicy(max_tries=5), on_failure=_mark_failed)
async def send_email(run: JobRun, message_id: uuid.UUID) -> bool:
    sender: EmailSender = run.ctx["email_sender"]
    try:
        return await email_service.deliver(run.session, sender, message_id)
    except EmailRejectedError as error:
        raise EmailRejectedJobError() from error
