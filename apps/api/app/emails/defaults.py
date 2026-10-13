"""The candidate email templates every workspace starts with (FR-MSG-01, NOTIFICATIONS.md §1-2).

Wording follows VOICE_AND_TONE.md: first-name greeting, short paragraphs, one clear link, signed
by the company's hiring team, no exclamation marks. The interview invitation is the canvas
EditEmailTemplate frame's copy. Rejection templates don't carry the human-review line: it is
added to every rejection email when it is rendered (ADR-015), and the editor shows it locked.

Workspaces keep their own copy of this wording in `email_templates`, so editing a default here
changes only workspaces created (or templates reset) afterwards.
"""

from dataclasses import dataclass
from enum import StrEnum


class TemplateKey(StrEnum):
    INTERVIEW_INVITATION = "interview_invitation"
    INTERVIEW_REMINDER = "interview_reminder"
    FINISH_INTERVIEW = "finish_interview"
    INTERVIEW_RECEIVED = "interview_received"
    NEXT_STAGE = "next_stage"
    REJECT_RESUME = "reject_resume"
    REJECT_INTERVIEW = "reject_interview"
    ROLE_CLOSED = "role_closed"
    REVIEW_RECEIVED = "review_received"
    REVIEW_UPHELD = "review_upheld"


# Every template can use these.
BASE_PARAMETERS = ("Candidate.firstname", "Candidate.lastname", "Job.title", "Company.name")
INTERVIEW_PARAMETERS = ("Interview.link", "Interview.expiry")
REVIEW_LINK = "Review.link"

# Parameters whose value is a URL: shown as a link when they stand in the text.
LINK_PARAMETERS = frozenset({"Interview.link", REVIEW_LINK})

INTERVIEW_KEYS = frozenset(
    {TemplateKey.INTERVIEW_INVITATION, TemplateKey.INTERVIEW_REMINDER, TemplateKey.FINISH_INTERVIEW}
)
# Automated "not moving forward" emails: they always carry the review line (ADR-015).
REJECTION_KEYS = frozenset({TemplateKey.REJECT_RESUME, TemplateKey.REJECT_INTERVIEW})

# The locked footer line of rejection emails (SCREEN_SPECS.md A-07).
REVIEW_LINE_HTML = f"<p>Want a person to review this decision? [{REVIEW_LINK}]</p>"


def parameters_for(key: TemplateKey) -> tuple[str, ...]:
    """The parameters a template may use. An interview link only exists for the interview
    emails, and a review link only for rejections, so anything else would be sent unfilled."""
    if key in INTERVIEW_KEYS:
        return BASE_PARAMETERS + INTERVIEW_PARAMETERS
    if key in REJECTION_KEYS:
        return (*BASE_PARAMETERS, REVIEW_LINK)
    return BASE_PARAMETERS


@dataclass(frozen=True)
class DefaultTemplate:
    key: TemplateKey
    subject: str
    body_html: str


def _body(*paragraphs: str) -> str:
    greeting = "<p>Hi [Candidate.firstname],</p>"
    sign_off = "<p>The [Company.name] hiring team</p>"
    return "".join([greeting, *(f"<p>{p}</p>" for p in paragraphs), sign_off])


DEFAULTS: dict[TemplateKey, DefaultTemplate] = {
    template.key: template
    for template in (
        DefaultTemplate(
            TemplateKey.INTERVIEW_INVITATION,
            "You're invited to interview with [Company.name]",
            _body(
                "Thanks for applying for the [Job.title] role at [Company.name]. We enjoyed "
                "reading your résumé and would like to learn more about you.",
                "The next step is a short AI interview you can take whenever it suits you. There "
                "are no trick questions, just a conversation about your experience.",
                "Start your interview here: [Interview.link]",
                "Your link is open until [Interview.expiry].",
                "Good luck. We're looking forward to hearing from you.",
            ),
        ),
        DefaultTemplate(
            TemplateKey.INTERVIEW_REMINDER,
            "Your interview for [Job.title] is waiting",
            _body(
                "Your AI interview for the [Job.title] role at [Company.name] is still waiting "
                "for you. You can take it whenever it suits you before the link closes.",
                "Start your interview here: [Interview.link]",
                "Your link is open until [Interview.expiry].",
            ),
        ),
        DefaultTemplate(
            TemplateKey.FINISH_INTERVIEW,
            "[Candidate.firstname], pick up where you left off",
            _body(
                "It looks like your interview for the [Job.title] role at [Company.name] "
                "stopped before the end. That happens, and you can come back to finish it.",
                "Continue your interview here: [Interview.link]",
                "Your link is open until [Interview.expiry].",
            ),
        ),
        DefaultTemplate(
            TemplateKey.INTERVIEW_RECEIVED,
            "We've received your interview for [Job.title]",
            _body(
                "Thank you for taking the time to interview for the [Job.title] role at "
                "[Company.name]. Your interview is complete, and our hiring team will review it.",
                "A person on our team makes every hiring decision. We'll be in touch about the "
                "next steps.",
            ),
        ),
        DefaultTemplate(
            TemplateKey.NEXT_STAGE,
            "Good news about your [Job.title] application",
            _body(
                "Thank you for interviewing for the [Job.title] role at [Company.name]. We'd like "
                "to move you to the next stage of our hiring process.",
                "Someone from our team will be in touch soon with the details.",
            ),
        ),
        DefaultTemplate(
            TemplateKey.REJECT_RESUME,
            "An update on your application",
            _body(
                "Thank you for applying for the [Job.title] role at [Company.name] and for your "
                "interest in joining us.",
                "We've reviewed your résumé against what this role needs, and we won't be moving "
                "forward with your application this time.",
                "We'd be glad to see you apply for other roles with us in the future.",
            ),
        ),
        DefaultTemplate(
            TemplateKey.REJECT_INTERVIEW,
            "Thank you for interviewing with us",
            _body(
                "Thank you for taking the time to interview for the [Job.title] role at "
                "[Company.name].",
                "We've reviewed your interview, and we won't be moving forward with your "
                "application for this role. We know this isn't the news you were hoping for.",
                "We'd be glad to see you apply for other roles with us in the future.",
            ),
        ),
        DefaultTemplate(
            TemplateKey.ROLE_CLOSED,
            "An update on the [Job.title] role",
            _body(
                "Thank you for your interest in the [Job.title] role at [Company.name]. We've "
                "closed this role, so we won't be moving forward with applications for it.",
                "We appreciate the time you put into applying, and we'd be glad to see you apply "
                "for other roles with us in the future.",
            ),
        ),
        DefaultTemplate(
            TemplateKey.REVIEW_RECEIVED,
            "We've received your request for a review",
            _body(
                "Thank you for asking for a person to review the decision on your [Job.title] "
                "application at [Company.name]. We've received your request.",
                "Someone from our hiring team will look at your application and let you know the "
                "outcome by email.",
            ),
        ),
        DefaultTemplate(
            TemplateKey.REVIEW_UPHELD,
            "The outcome of your review request",
            _body(
                "Thank you for your patience. A person on our hiring team has reviewed the "
                "decision on your [Job.title] application at [Company.name].",
                "After looking at your application again, we're keeping our original decision, so "
                "we won't be moving forward this time. We know this isn't the news you were "
                "hoping for.",
                "We'd be glad to see you apply for other roles with us in the future.",
            ),
        ),
    )
}
