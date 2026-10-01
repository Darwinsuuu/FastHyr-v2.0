"""Email delivery (ADR-008): Resend in the cloud, local Mailpit over SMTP, or a log-only sender.
Only the `send_email` job calls these. Nothing here logs addresses or content, only IDs."""

import asyncio
import logging
import smtplib
import uuid
from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage
from email.utils import formataddr
from typing import Protocol

import httpx2

from app.core.config import Settings

logger = logging.getLogger("app.email")

RESEND_URL = "https://api.resend.com/emails"


@dataclass(frozen=True)
class OutgoingEmail:
    id: uuid.UUID  # the email_messages row; also the provider idempotency key
    to: str
    from_name: str
    subject: str
    html: str
    text: str


class EmailRejectedError(Exception):
    """The provider refused this email (bad address, blocked sender). Retrying won't help."""

    code = "provider_rejected"


class EmailUnavailableError(Exception):
    """The provider couldn't be reached or failed. Worth retrying."""

    code = "provider_unavailable"


class EmailSender(Protocol):
    async def send(self, email: OutgoingEmail) -> str:
        """Sends `email` and returns the provider's message ID."""
        ...


class ResendSender:
    def __init__(self, api_key: str, from_address: str, *, timeout: float = 15) -> None:
        self.api_key = api_key
        self.from_address = from_address
        self.timeout = timeout

    async def send(self, email: OutgoingEmail) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            # A retried send of the same row is dropped by Resend instead of sent twice.
            "Idempotency-Key": str(email.id),
        }
        payload = {
            "from": formataddr((email.from_name, self.from_address)),
            "to": [email.to],
            "subject": email.subject,
            "html": email.html,
            "text": email.text,
            "tags": [{"name": "message_id", "value": str(email.id)}],
        }
        try:
            async with httpx2.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(RESEND_URL, json=payload, headers=headers)
        except httpx2.HTTPError as error:
            raise EmailUnavailableError() from error
        if response.status_code == 429 or response.status_code >= 500:
            raise EmailUnavailableError()
        if response.status_code >= 400:
            # The body can repeat the address, so only the status is logged.
            logger.warning("resend rejected message %s (%d)", email.id, response.status_code)
            raise EmailRejectedError()
        provider_id: str = response.json()["id"]
        return provider_id


class SmtpSender:
    """Local development: hands the email to Mailpit (http://127.0.0.1:54324) to look at."""

    def __init__(self, host: str, port: int, from_address: str) -> None:
        self.host = host
        self.port = port
        self.from_address = from_address

    async def send(self, email: OutgoingEmail) -> str:
        message = MimeMessage()
        message["From"] = formataddr((email.from_name, self.from_address))
        message["To"] = email.to
        message["Subject"] = email.subject
        message["X-FastHyr-Message-Id"] = str(email.id)
        message.set_content(email.text)
        message.add_alternative(email.html, subtype="html")

        def deliver() -> None:
            with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
                smtp.send_message(message)

        try:
            await asyncio.to_thread(deliver)
        except (OSError, smtplib.SMTPException) as error:
            raise EmailUnavailableError() from error
        return f"smtp-{email.id}"


class LogSender:
    """Sends nothing: records that the email would have gone out. For environments without a
    Resend key."""

    async def send(self, email: OutgoingEmail) -> str:
        logger.info("email %s not sent (no email provider configured)", email.id)
        return f"log-{email.id}"


def sender_from_settings(settings: Settings) -> EmailSender:
    backend = settings.resolved_email_backend
    if backend == "resend":
        return ResendSender(settings.resend_api_key, settings.email_from_address)
    if backend == "smtp":
        return SmtpSender(settings.smtp_host, settings.smtp_port, settings.email_from_address)
    return LogSender()
