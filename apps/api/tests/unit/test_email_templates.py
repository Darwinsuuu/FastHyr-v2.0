"""MSG-001: the default candidate emails, the save checks and the review line on rejections."""

import pytest

from app.core.errors import EmailTemplateInvalidError
from app.emails.candidate import MissingParameterError, render_template
from app.emails.defaults import DEFAULTS, REJECTION_KEYS, TemplateKey, parameters_for
from app.emails.render import Branding, RenderedEmail
from app.services.email_templates import validate

VALUES = {
    "Candidate.firstname": "Bea",
    "Candidate.lastname": "Garcia",
    "Job.title": "Senior Backend Engineer",
    "Company.name": "Acme Talent",
    "Interview.link": "https://dev.fasthyr.com/interview/abc",
    "Interview.expiry": "Fri, 10 Oct 2026, 11:59 PM PHT",
    "Review.link": "https://dev.fasthyr.com/review/xyz",
}
REVIEW_LINE = "Want a person to review this decision?"


def render(
    key: TemplateKey, subject: str, body_html: str, values: dict[str, str] = VALUES
) -> RenderedEmail:
    return render_template(
        key=key,
        subject=subject,
        body_html=body_html,
        values=values,
        site_url="https://dev.fasthyr.com",
        branding=Branding("Acme Talent"),
    )


def test_there_is_a_default_for_every_key_and_each_passes_its_own_checks() -> None:
    assert set(DEFAULTS) == set(TemplateKey)
    assert len(DEFAULTS) == 9
    for key, default in DEFAULTS.items():
        assert validate(key, default.subject, default.body_html) == (
            default.subject,
            default.body_html,
        )
        text = render(key, default.subject, default.body_html).text
        assert text.startswith("Hi Bea,")
        assert "[" not in text
        assert "!" not in default.subject + default.body_html


@pytest.mark.parametrize("key", sorted(REJECTION_KEYS))
def test_rejections_always_render_the_review_line(key: TemplateKey) -> None:
    # The editor removed the line: it is added back, with the link.
    email = render(key, "An update", "<p>Hi [Candidate.firstname], not this time.</p>")
    assert f"{REVIEW_LINE} https://dev.fasthyr.com/review/xyz" in email.text
    assert 'href="https://dev.fasthyr.com/review/xyz"' in email.html

    # Kept where the editor put it, and only once.
    body = "<p>Ask for a review: [Review.link]</p><p>Thanks</p>"
    email = render(key, "An update", body)
    assert email.text.count("https://dev.fasthyr.com/review/xyz") == 1
    assert REVIEW_LINE not in email.text


def test_other_templates_have_no_review_line() -> None:
    default = DEFAULTS[TemplateKey.ROLE_CLOSED]
    email = render(TemplateKey.ROLE_CLOSED, default.subject, default.body_html)
    assert REVIEW_LINE not in email.text


def test_a_parameter_without_a_value_is_never_sent_as_written() -> None:
    default = DEFAULTS[TemplateKey.INTERVIEW_INVITATION]
    values = {k: v for k, v in VALUES.items() if k != "Interview.link"}
    with pytest.raises(MissingParameterError, match=r"Interview\.link"):
        render(TemplateKey.INTERVIEW_INVITATION, default.subject, default.body_html, values)


def test_unknown_parameters_are_rejected_on_save() -> None:
    with pytest.raises(EmailTemplateInvalidError) as raised:
        validate(
            TemplateKey.REJECT_RESUME,
            "Hi [Candidate.first_name]",
            "<p>[Interview.link] [Foo.bar] [sic] [Job.title] [Foo.bar]</p>",
        )
    assert raised.value.errors == [
        {"loc": ["body", "subject"], "type": "unknown_parameter", "msg": "[Candidate.first_name]"},
        {"loc": ["body", "body_html"], "type": "unknown_parameter", "msg": "[Interview.link]"},
        {"loc": ["body", "body_html"], "type": "unknown_parameter", "msg": "[Foo.bar]"},
    ]


def test_each_template_takes_only_the_parameters_it_can_fill() -> None:
    assert "Review.link" not in parameters_for(TemplateKey.INTERVIEW_INVITATION)
    assert "Interview.link" in parameters_for(TemplateKey.INTERVIEW_REMINDER)
    assert "Review.link" in parameters_for(TemplateKey.REJECT_INTERVIEW)
    assert "Interview.expiry" not in parameters_for(TemplateKey.NEXT_STAGE)
    with pytest.raises(EmailTemplateInvalidError):
        validate(TemplateKey.INTERVIEW_INVITATION, "Hi", "<p>[Review.link]</p>")


def test_save_cleans_the_message_and_needs_a_subject_and_text() -> None:
    subject, body = validate(
        TemplateKey.NEXT_STAGE,
        "  Good   news ",
        '<p onclick="x">Hi <img src=x><script>alert(1)</script><a href="javascript:x">us</a></p>',
    )
    assert subject == "Good news"
    assert body == '<p>Hi <a rel="noopener noreferrer">us</a></p>'

    with pytest.raises(EmailTemplateInvalidError) as raised:
        validate(TemplateKey.NEXT_STAGE, " ", "<p> </p><script>x</script>")
    assert [(e["loc"][1], e["type"]) for e in raised.value.errors] == [
        ("subject", "missing"),
        ("body_html", "missing"),
    ]


def test_link_parameters_in_the_text_become_links() -> None:
    email = render(
        TemplateKey.INTERVIEW_INVITATION,
        "Hi",
        '<p>Start: [Interview.link]</p><p><a href="[Interview.link]">Start my interview</a></p>',
    )
    assert email.html.count('href="https://dev.fasthyr.com/interview/abc"') == 2
    assert '<a href="<a' not in email.html
