"""Two-pass résumé redaction (AI_PIPELINE.md §1 step 2, BIAS_FAIRNESS.md, FR-SCREEN-02).

1. Rules (`redact_rules`): contact details, links, labelled personal lines, ages, graduation
   years, street addresses and the candidate's own name, all found without a model.
2. Model (`redact`): `resume_redaction@v1` reads the rule-redacted text and returns the spans
   rules can't find reliably (other names, gender markers, school names, addresses, photo
   captions); every whole-word occurrence of each span is masked.

Masks are readable labels such as `[NAME]` or `[YEAR]`, so later steps still see that something
was there. The redacted text is the only résumé text any scoring step sees; the original stays in
the PDF for the hiring team. Nothing here logs résumé text.
"""

import re
import uuid
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

from app.ai.client import AIClient
from app.ai.prompts import load_prompt
from app.ai.schemas.resume_redaction import ResumeRedaction, SpanKind

PROMPT = ("resume_redaction", 1)
RULES_VERSION = "rules@v1"
VERSION = f"{RULES_VERSION}+{PROMPT[0]}@v{PROMPT[1]}"

MASKS: dict[str, str] = {
    "email": "[EMAIL]",
    "link": "[LINK]",
    "phone": "[PHONE]",
    "address": "[ADDRESS]",
    "birth": "[DATE OF BIRTH]",
    "age": "[AGE]",
    "year": "[YEAR]",
    "name": "[NAME]",
    "gender": "[GENDER]",
    "school": "[SCHOOL]",
    "personal": "[PERSONAL DETAIL]",
    "photo": "[PHOTO]",
}
# Spans shorter than this are ignored: masking every "A" or "Jo" would wreck the text.
MIN_SPAN = 2


@dataclass
class Redaction:
    text: str
    masked: Counter[str] = field(default_factory=Counter)

    def mask(self, kind: str, pattern: re.Pattern[str], *, group: int = 0) -> None:
        """Replaces every match of `pattern` (or of its `group`) with the mask for `kind`."""

        def replace(match: re.Match[str]) -> str:
            self.masked[kind] += 1
            if group == 0:
                return MASKS[kind]
            start, end = match.span(group)
            offset = match.start()
            whole = match.group(0)
            return whole[: start - offset] + MASKS[kind] + whole[end - offset :]

        self.text = pattern.sub(replace, self.text)


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
# Profile links people write without a scheme.
_PROFILE = re.compile(
    r"\b(?:[\w-]+\.)*(?:linkedin\.com|github\.com|gitlab\.com|behance\.net|dribbble\.com|"
    r"medium\.com|facebook\.com|instagram\.com|twitter\.com|x\.com)/\S*",
    re.IGNORECASE,
)
_PHONE_CANDIDATE = re.compile(r"(?<![\w+])\+?\(?\d[\d\s().-]{5,}\d(?!\w)")
_YEAR_RANGE = re.compile(r"^(?:19|20)\d\d\s*[-\u2013\u2014]\s*(?:19|20)\d\d$")
_DATE = re.compile(r"^\d{1,4}[./-]\d{1,2}[./-]\d{1,4}$")
_PERSONAL_LABELS = {
    "address": r"(?:home |permanent |current |present |mailing |residential )?address|"
    r"residence|location",
    "birth": r"date of birth|birth ?date|birthday|d\.?o\.?b\.?|born|place of birth|birthplace",
    "age": r"age",
    "gender": r"gender|sex",
    "personal": r"civil status|marital status|nationality|citizenship|religion|height|weight|"
    r"ethnicity|race|dependents|children|spouse|father'?s name|mother'?s name|"
    r"languages? spoken at home|blood type|sss|tin|pag-?ibig|philhealth|passport(?: no\.?)?",
}
_LABELLED = {
    kind: re.compile(rf"(?im)^([ \t•·*-]*(?:{labels})\s*(?::|\s-\s)\s*)(.+)$")
    for kind, labels in _PERSONAL_LABELS.items()
}
_YEARS_OLD = re.compile(r"\b\d{2}\s*(?:years?|yrs?)[\s-]*old\b", re.IGNORECASE)
_GRADUATION = re.compile(
    r"\b(?:class of|batch|graduated(?: in)?|graduating(?: in)?|graduation(?: year)?:?|"
    r"expected(?: graduation)?:?)\s*((?:19|20)\d\d)\b",
    re.IGNORECASE,
)
_STREET = re.compile(
    r"\b\d+[A-Za-z]?(?:\s+[A-Z][\w.'-]*){1,5}\s+(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|"
    r"Boulevard|Blvd\.?|Drive|Dr\.?|Lane|Ln\.?|Highway|Hwy\.?|Way|Court|Ct\.?)(?=\W|$)[^\n]*"
)
# Philippine address parts, only when followed by a name ("Brgy. San Isidro"), so "barangay
# health centres" in a job entry stays.
_BARANGAY = re.compile(r"\b(?:Brgy\.?|BRGY\.?|Barangay|BARANGAY|Purok|Sitio)\s+[A-Z0-9][^\n]*")
_YEAR = re.compile(r"\b(?:19|20)\d\d\b")
_EDUCATION_HEADING = re.compile(
    r"(?i)^\W*(?:education(?:al background| and training| & training)?|academic "
    r"(?:background|history|qualifications)|qualifications|schools? attended)\W*$"
)
# A heading that ends the Education section: a short line naming another section.
_OTHER_HEADING = re.compile(
    r"(?i)^\W*(?:(?:work |professional |relevant )?experience|employment(?: history)?|"
    r"work history|career(?: history| summary)?|skills|technical skills|projects|"
    r"certifications?|licen[cs]es|awards|achievements|publications|volunteer(?:ing| work)?|"
    r"leadership|activities|interests|languages|references|summary|profile|objective|"
    r"about me|trainings?(?: and seminars)?|seminars|affiliations|"
    r"personal(?: details| information| data)?)\W*$"
)


def redact_rules(text: str, known_names: Iterable[str] = ()) -> Redaction:
    """The deterministic pass. `known_names` are names the application gave (the candidate's
    full name); each is masked whole, and each part of it when written capitalised."""
    redaction = Redaction(text)
    redaction.mask("email", _EMAIL)
    redaction.mask("link", _URL)
    redaction.mask("link", _PROFILE)
    _mask_phones(redaction)
    for kind, pattern in _LABELLED.items():
        redaction.mask(kind, pattern, group=2)
    redaction.mask("age", _YEARS_OLD)
    redaction.mask("year", _GRADUATION, group=1)
    redaction.mask("address", _STREET)
    redaction.mask("address", _BARANGAY)
    _mask_education_years(redaction)
    for name in known_names:
        _mask_name(redaction, name)
    return redaction


def _mask_phones(redaction: Redaction) -> None:
    def replace(match: re.Match[str]) -> str:
        found = match.group(0).strip("() ")
        digits = sum(char.isdigit() for char in found)
        if digits < 7 or digits > 15 or _YEAR_RANGE.match(found) or _DATE.match(found):
            return match.group(0)
        redaction.masked["phone"] += 1
        return MASKS["phone"]

    redaction.text = _PHONE_CANDIDATE.sub(replace, redaction.text)


def _mask_education_years(redaction: Redaction) -> None:
    """Every year inside an Education section (graduation years reveal age; G2). Years in the
    work history stay: they are job evidence."""
    lines = redaction.text.split("\n")
    in_education = False
    for index, line in enumerate(lines):
        if _EDUCATION_HEADING.match(line):
            in_education = True
            continue
        if _OTHER_HEADING.match(line):
            in_education = False
            continue
        if in_education:
            masked, count = _YEAR.subn(MASKS["year"], line)
            if count:
                lines[index] = masked
                redaction.masked["year"] += count
    redaction.text = "\n".join(lines)


def _mask_name(redaction: Redaction, name: str) -> None:
    parts = [part for part in re.split(r"[\s,]+", name.strip()) if len(part) >= MIN_SPAN]
    if not parts:
        return
    whole = r"\s+".join(re.escape(part) for part in parts)
    redaction.mask("name", re.compile(rf"(?<!\w){whole}(?!\w)", re.IGNORECASE))
    for part in parts:
        if len(part) < 3:
            continue
        # Capitalised or upper case only, so a surname that is also a word ("Young", "Rice")
        # isn't masked in running text.
        variants = {part.capitalize(), part.upper()} | ({part} if not part.islower() else set())
        alternatives = "|".join(re.escape(variant) for variant in variants)
        redaction.mask("name", re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)"))


def apply_spans(redaction: Redaction, spans: Iterable[tuple[SpanKind, str]]) -> None:
    """Masks every whole-word occurrence of each span (case-insensitive). Longer spans go first
    so "Ateneo de Manila University" is masked before "Ateneo". Spans the text doesn't contain
    are ignored."""
    for kind, span in sorted(set(spans), key=lambda item: -len(item[1])):
        span = span.strip()
        if len(span) < MIN_SPAN or span in MASKS.values():
            continue
        pattern = r"\s+".join(re.escape(part) for part in span.split())
        redaction.mask(kind, re.compile(rf"(?<!\w){pattern}(?!\w)", re.IGNORECASE))


async def redact(
    ai: AIClient,
    text: str,
    *,
    known_names: Iterable[str] = (),
    workspace_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
) -> Redaction:
    """Both passes. The model sees only the rule-redacted text."""
    redaction = redact_rules(text, known_names)
    answer = await ai.structured(
        purpose="resume_redaction",
        prompt=load_prompt(*PROMPT),
        variables={"resume_text": redaction.text},
        schema=ResumeRedaction,
        workspace_id=workspace_id,
        entity_id=entity_id,
        temperature=0,
    )
    apply_spans(redaction, ((span.kind, span.text) for span in answer.spans))
    return redaction
