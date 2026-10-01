"""Versioned prompts: `prompts/<name>@v<N>.md`, never edited once released; a change is a new
version (AI_PIPELINE.md). A prompt file has two sections:

    # System
    You assess résumés for ${job_title} ...

    # User
    ${resume_text}

`${name}` placeholders are filled with `string.Template`; a missing value is an error, so a
prompt can't silently go out half-filled.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from string import Template

PROMPTS_DIR = Path(__file__).parent / "prompts"
SECTION = re.compile(r"^# (System|User)\s*$", re.MULTILINE)


class PromptError(Exception):
    """A prompt file is missing, malformed, or a placeholder has no value."""


@dataclass(frozen=True)
class RenderedPrompt:
    version: str  # "<name>@v<N>", logged in ai_calls.prompt_version
    system: str
    user: str


@dataclass(frozen=True)
class Prompt:
    name: str
    version: int
    system: Template
    user: Template

    @property
    def tag(self) -> str:
        return f"{self.name}@v{self.version}"

    def render(self, variables: dict[str, str]) -> RenderedPrompt:
        try:
            return RenderedPrompt(
                version=self.tag,
                system=self.system.substitute(variables).strip(),
                user=self.user.substitute(variables).strip(),
            )
        except (KeyError, ValueError) as error:
            raise PromptError(f"{self.tag}: missing or bad placeholder {error}") from error


def load_prompt(name: str, version: int, directory: Path = PROMPTS_DIR) -> Prompt:
    path = directory / f"{name}@v{version}.md"
    if not path.is_file():
        raise PromptError(f"no prompt file {path.name}")
    parts = SECTION.split(path.read_text(encoding="utf-8"))
    # ["<preamble>", "System", "<text>", "User", "<text>"]
    sections = dict(zip(parts[1::2], parts[2::2], strict=True))
    if set(sections) != {"System", "User"}:
        raise PromptError(f"{path.name} needs exactly one '# System' and one '# User' section")
    return Prompt(name, version, Template(sections["System"]), Template(sections["User"]))
