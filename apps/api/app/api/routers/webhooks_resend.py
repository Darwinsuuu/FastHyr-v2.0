"""Resend delivery webhooks (API.md "Webhooks", NOTIFICATIONS.md §5): signature-checked,
then the email's status moves to delivered, bounced, complained or failed."""

import json
from typing import Annotated

from fastapi import APIRouter, Header, Request, status

from app.api.deps import Session
from app.core.errors import PROBLEM_RESPONSES, InvalidWebhookSignatureError
from app.integrations import resend_webhook
from app.services import emails as email_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"], responses=PROBLEM_RESPONSES)


@router.post("/resend", status_code=status.HTTP_204_NO_CONTENT)
async def resend_webhook_event(
    request: Request,
    session: Session,
    svix_id: Annotated[str | None, Header()] = None,
    svix_timestamp: Annotated[str | None, Header()] = None,
    svix_signature: Annotated[str | None, Header()] = None,
) -> None:
    """Unknown events and emails are accepted and ignored, so Resend doesn't retry them."""
    body = await request.body()
    secret: str = request.app.state.settings.resend_webhook_secret
    if not resend_webhook.verify(
        secret,
        message_id=svix_id,
        timestamp=svix_timestamp,
        signatures=svix_signature,
        body=body,
    ):
        raise InvalidWebhookSignatureError()
    try:
        event = json.loads(body)
        event_type, provider_id = event["type"], event["data"]["email_id"]
    except (ValueError, KeyError, TypeError):
        return
    if isinstance(event_type, str) and isinstance(provider_id, str):
        await email_service.apply_webhook_event(
            session, event_type, provider_id, hard_bounce=_hard_bounce(event["data"])
        )


def _hard_bounce(data: dict[str, object]) -> bool:
    """Resend's `email.bounced` is a permanent failure; its `bounce.type` says so ("Permanent").
    Only an explicit other type ("Transient", "Undetermined") counts as soft."""
    bounce = data.get("bounce")
    kind = bounce.get("type") if isinstance(bounce, dict) else None
    return not isinstance(kind, str) or kind == "Permanent"
