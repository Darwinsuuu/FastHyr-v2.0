"""FND-010: email bodies keep only the allow-listed HTML, parameter values are escaped, every
email has a plain-text part, and Resend webhook signatures are checked."""

import time
from datetime import UTC, datetime

from app.emails import system
from app.emails.render import Button, html_to_text, render, sanitize
from app.integrations.resend_webhook import sign, verify

SECRET = "whsec_dGVzdC1zZWNyZXQtZm9yLWZhc3RoeXI="


def test_sanitize_keeps_only_the_allow_list() -> None:
    dirty = (
        '<p onclick="steal()">Hi <strong>there</strong> <em>you</em></p>'
        "<script>alert(1)</script><img src=x onerror=alert(1)>"
        '<a href="javascript:alert(1)">bad</a> <a href="https://acme.com" style="x">good</a>'
        "<ul><li>one</li></ul><h1>Big</h1><iframe src=https://x></iframe>"
    )

    clean = sanitize(dirty)

    assert "<p>Hi <strong>there</strong> <em>you</em></p>" in clean
    for banned in ("onclick", "script", "alert", "<img", "javascript:", "style=", "<h1", "iframe"):
        assert banned not in clean
    assert '<a href="https://acme.com" rel="noopener noreferrer">good</a>' in clean
    assert "<ul><li>one</li></ul>" in clean


def test_parameter_values_are_escaped_and_unknown_ones_kept() -> None:
    email = render(
        subject="Hello [Candidate.firstname]",
        body_html="<p>Hi [Candidate.firstname], about [Job.title] at [Unknown.thing]</p>",
        parameters={"Candidate.firstname": "<script>Bea</script>", "Job.title": "Engineer & lead"},
        site_url="https://fasthyr.com",
        company="Acme Talent",
    )

    assert email.subject == "Hello <script>Bea</script>"  # plain text, never HTML
    assert "&lt;script&gt;Bea&lt;/script&gt;" in email.html
    assert "<script>Bea" not in email.html
    assert "Engineer &amp; lead" in email.html
    assert "[Unknown.thing]" in email.html
    assert "Sent by Acme Talent via FastHyr" in email.html


def test_plain_text_alternative_keeps_paragraphs_bullets_and_links() -> None:
    email = render(
        subject="Interview",
        body_html=(
            "<p>Hi Bea,</p><p>Your interview is ready.<br>It takes 30 minutes.</p>"
            '<ul><li>Quiet room</li><li>Good light</li></ul><p>See <a href="https://a.co/x">this</a>'
            "</p>"
        ),
        button=Button("Start interview", "https://app.fasthyr.com/i/abc"),
        site_url="https://fasthyr.com",
        company="Acme Talent",
    )

    assert email.text == (
        "Hi Bea,\n\nYour interview is ready.\nIt takes 30 minutes.\n\n- Quiet room\n- Good light"
        "\n\nSee this (https://a.co/x)\n\nStart interview: https://app.fasthyr.com/i/abc"
        "\n\nSent by Acme Talent via FastHyr\n"
    )
    assert "<" not in email.text


def test_html_to_text_drops_markup() -> None:
    assert html_to_text("<p>One &amp; two</p><p>Three</p>") == "One & two\n\nThree"


def test_member_invite_carries_the_join_link_and_code() -> None:
    email = system.member_invite(
        site_url="https://fasthyr.com/",
        workspace_name="Acme <Talent>",
        inviter_name="Ana Cruz",
        role="hiring_manager",
        code="AB23-CD45",
        token="tok_abc",
        expires_at=datetime(2026, 10, 8, 9, tzinfo=UTC),
    )

    assert email.subject == "Ana Cruz invited you to join Acme <Talent> on FastHyr"
    assert 'href="https://fasthyr.com/join/tok_abc"' in email.html
    assert "AB23-CD45" in email.html
    assert "Acme &lt;Talent&gt;" in email.html
    assert "https://fasthyr.com/join/tok_abc" in email.text
    assert "AB23-CD45" in email.text
    assert "a Hiring manager" in email.text
    assert "8 Oct 2026" in email.text


def test_webhook_signature_must_match_and_be_recent() -> None:
    body = b'{"type":"email.delivered","data":{"email_id":"re_1"}}'
    now = time.time()
    stamp = str(int(now))
    good = sign(SECRET, message_id="msg_1", timestamp=stamp, body=body)

    def check(**overrides: object) -> bool:
        values: dict[str, object] = {
            "message_id": "msg_1",
            "timestamp": stamp,
            "signatures": f"v1,stale {good}",
            "body": body,
            "now": now,
        }
        values.update(overrides)
        return verify(SECRET, **values)  # type: ignore[arg-type]

    assert check()
    assert not check(body=body.replace(b"delivered", b"bounced"))
    assert not check(message_id="msg_2")
    assert not check(signatures="v1,AAAA")
    assert not check(now=now + 6 * 60)  # replayed too late
    assert not check(signatures=None)
    assert not verify("", message_id="msg_1", timestamp=stamp, signatures=good, body=body)
