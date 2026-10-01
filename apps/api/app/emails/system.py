"""System emails (NOTIFICATIONS.md §4): fixed copy, not editable by workspaces. Each builder
returns the rendered email; `services/emails.py` queues it."""

from datetime import datetime
from html import escape

from app.emails.render import Button, RenderedEmail, render

FROM_FASTHYR = "FastHyr"

ROLE_NAMES = {"admin": "an Admin", "recruiter": "a Recruiter", "hiring_manager": "a Hiring manager"}


def member_invite(
    *,
    site_url: str,
    workspace_name: str,
    inviter_name: str | None,
    role: str,
    code: str,
    token: str,
    expires_at: datetime,
) -> RenderedEmail:
    """The member invite (WS-004, AUTH-004): a link to `/join/{token}` and the code, 7 days."""
    inviter = inviter_name or "A teammate"
    link = f"{site_url.rstrip('/')}/join/{token}"
    expiry = expires_at.strftime("%-d %b %Y")
    return render(
        subject=f"{inviter} invited you to join {workspace_name} on FastHyr",
        preheader=f"Join {workspace_name} on FastHyr. The invite works until {expiry}.",
        heading=f"Join {workspace_name} on FastHyr",
        body_html=(
            f"<p>{escape(inviter)} invited you to join {escape(workspace_name)} as "
            f"{ROLE_NAMES.get(role, 'a member')}. Sign in with this email address to accept.</p>"
        ),
        button=Button(f"Join {workspace_name}", link),
        after_html=(
            '<p style="margin:0 0 16px;font-size:14px;line-height:21px;color:#5A625D;">'
            "Or sign in, choose Join a workspace and enter this code: "
            f'<strong style="color:#1E2A26;letter-spacing:1px;">{escape(code)}</strong></p>'
            '<p style="margin:0;font-size:14px;line-height:21px;color:#5A625D;">'
            f"The invite works until {escape(expiry)}. If you weren't expecting it, you can "
            "ignore this email.</p>"
        ),
        site_url=site_url,
    )


def test_email(*, site_url: str, workspace_name: str) -> RenderedEmail:
    """A check that email reaches the sender's inbox, sent to their own address."""
    return render(
        subject="FastHyr test email",
        heading="Your email works",
        body_html=(
            "<p>This is a test email from FastHyr. If you can read it, emails from "
            f"{escape(workspace_name)} are reaching your inbox.</p>"
        ),
        site_url=site_url,
        company=workspace_name,
    )
