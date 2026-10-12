"""Sample applicants for the Acme Talent seed (DASH-003): every credit a sample pipeline used is
one application, so the dashboards, lists and credit pages agree with each other.

Everything here is synthetic. Names come from the design's sample people, emails use the reserved
`.test` domain, and the same `random.Random` seed gives the same people and stages on every
reset. Applications get a résumé screen, an interview link and, once they finished, a short
assessment: enough for counts and scores. Full résumé assessments, transcripts and reports for the
profile pages come with the tasks that show them.

States are chosen so no background job picks the rows up again: screened applications have an
interview plan, finished interviews have their recording, transcript and checks marked done, and
interviews still being scored show the transcript as processing.
"""

import hashlib
import random
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_days import end_of_day_after
from app.integrations.storage import recording_file_path
from app.models import (
    Application,
    Assessment,
    Base,
    Candidate,
    IntegrityFlag,
    Interview,
    InterviewPlan,
    Pipeline,
    ResumeAssessment,
)
from app.services import credits
from scripts.seed_assessments import bea_garcia, sample_interview

# The design's sample people (frames PipelineView and CandidatePool).
FIRST_NAMES = (
    "Miguel", "Andrea", "Paolo", "Bea", "Carlo", "Jasmine", "Rafael", "Nicole", "Joshua",
    "Katrina", "Marco", "Patricia", "Enzo", "Denise", "Luis", "Camille", "Adrian", "Trisha",
    "Gabriel", "Monica", "Kevin", "Hannah", "Daniel", "Sofia",
)  # fmt: skip
LAST_NAMES = (
    "Villanueva", "Reyes", "Santos", "Cruz", "Bautista", "Garcia", "Mendoza", "Tan", "Lim",
    "Aquino", "Navarro", "Dela Cruz", "Ramos", "Castillo", "Uy", "Flores", "Ong", "Torres",
    "Salazar", "Chua",
)  # fmt: skip
CITIES = ("Makati City", "Quezon City", "Pasig City", "Taguig City", "Cebu City", "Davao City")
# Apply-link sources, weighted roughly like the Overview frame.
SOURCES = (
    ("linkedin", 45), ("jobstreet", 25), ("careers", 10), ("indeed", 6), ("kalibrr", 4),
    ("facebook", 3), ("other", 5), ("direct", 2),
)  # fmt: skip

# Senior Backend Engineer's strongest candidates in the frames (Overview, PipelineView):
# (name, score, open flag type or None). They are its latest finished interviews.
SHOWCASE = (
    ("Bea Garcia", 91, None),
    ("Marco Ong", 84, None),
    ("Nicole Aquino", 82, "second_voice"),
    ("Trisha Tan", 78, None),
    ("Luis Villanueva", 76, "read_aloud"),
)
SHOWCASE_PIPELINE = "Senior Backend Engineer"
SHOWCASE_NAMES = frozenset(name for name, _, _ in SHOWCASE)

RESUME_PASS_RATE = 0.6
# What people do with an interview link: finish it, leave partway, hit a technical problem,
# or never start (the rest).
FINISH, LEAVE, TECHNICAL = 0.72, 0.80, 0.83
FLAGGED = 0.02
# Of passed interviews assessed over three days ago: advanced, then rejected by the team; the
# rest still wait for a review.
ADVANCED, REJECTED = 0.45, 0.9
RETURNING = 0.12


@dataclass
class SampleCandidate:
    id: uuid.UUID
    full_name: str
    email: str
    applied: list[datetime] = field(default_factory=list)
    pipelines: set[uuid.UUID] = field(default_factory=set)


@dataclass(frozen=True)
class SampleApplication:
    id: uuid.UUID
    candidate: SampleCandidate
    applied_at: datetime
    source: str


class ApplicantMaker:
    """Makes the candidates and applications of every sample pipeline, sharing one pool of
    people so some apply more than once."""

    def __init__(self, workspace_id: uuid.UUID, namespace: uuid.UUID, email_domain: str) -> None:
        self.workspace_id = workspace_id
        self.namespace = namespace
        self.email_domain = email_domain
        self.rng = random.Random(20261010)
        # Must-have results and criterion scores (PIPE-008's fit explanation) draw from their own
        # generator, so the applications and stages above stay as they were.
        self.detail_rng = random.Random(20261012)
        # The assessments' content (ASMT-004) draws from a third, for the same reason.
        self.content_rng = random.Random(20261013)
        self.people: list[SampleCandidate] = []
        self.added: set[uuid.UUID] = set()
        # Rows written after the applications they refer to (see `add`).
        self.screens: list[Base] = []
        self.results: list[Base] = []

    def _person(self) -> SampleCandidate:
        name: str | None = None
        while name is None or name in SHOWCASE_NAMES:
            name = f"{self.rng.choice(FIRST_NAMES)} {self.rng.choice(LAST_NAMES)}"
        number = sum(1 for p in self.people if p.full_name == name) + 1
        local = name.lower().replace(" ", ".") + (f".{number}" if number > 1 else "")
        email = f"{local}@candidates.{self.email_domain}"
        person = SampleCandidate(uuid.uuid5(self.namespace, email), name, email)
        self.people.append(person)
        return person

    def plan(self, pipeline: Pipeline, count: int, until: datetime) -> list[SampleApplication]:
        """`count` applications spread over the pipeline's open days up to `until`, oldest
        first, a little busier towards the end like a role that's getting around."""
        start = pipeline.opens_at or until
        span = max((until - start).total_seconds(), 3600.0)
        names = [name for name, _, _ in SHOWCASE] if pipeline.title == SHOWCASE_PIPELINE else []
        applications: list[SampleApplication] = []
        for _ in range(count):
            offset = span * self.rng.random() ** 0.8
            applied_at = start + timedelta(seconds=min(offset, span - 60))
            person = self._returning(pipeline.id) or self._person()
            person.pipelines.add(pipeline.id)
            person.applied.append(applied_at)
            applications.append(SampleApplication(uuid.uuid4(), person, applied_at, self._source()))
        applications.sort(key=lambda a: a.applied_at)
        # The showcase people take the places of applicants who applied about two days ago, so
        # their interviews are finished and scored.
        if names:
            recent = [a for a in applications if until - a.applied_at > timedelta(days=2)]
            for application, name in zip(recent[-len(names) :], names, strict=False):
                person = application.candidate
                person.full_name = name
                person.email = f"{name.lower().replace(' ', '.')}@candidates.{self.email_domain}"
        return applications

    def _returning(self, pipeline_id: uuid.UUID) -> SampleCandidate | None:
        if not self.people or self.rng.random() >= RETURNING:
            return None
        person = self.rng.choice(self.people)
        return None if pipeline_id in person.pipelines else person

    def _source(self) -> str:
        names = [name for name, _ in SOURCES]
        return self.rng.choices(names, weights=[weight for _, weight in SOURCES])[0]

    async def add(
        self,
        session: AsyncSession,
        pipeline: Pipeline,
        applications: Sequence[SampleApplication],
        *,
        now: datetime,
        zone: ZoneInfo,
    ) -> None:
        """Uses one of the pipeline's credits per application, then writes the applications and
        everything that happened after they applied. The caller commits."""
        new_people = [a.candidate for a in applications if a.candidate.id not in self.added]
        for person in {p.id: p for p in new_people}.values():
            session.add(
                Candidate(
                    id=person.id,
                    workspace_id=self.workspace_id,
                    auth_user_id=uuid.uuid5(self.namespace, f"auth:{person.id}"),
                    email=person.email,
                    full_name=person.full_name,
                    phone_country_code="+63",
                    phone=f"917{self.rng.randrange(1_000_000, 9_999_999)}",
                    city=self.rng.choice(CITIES),
                    first_applied_at=min(person.applied),
                    last_activity_at=max(person.applied),
                )
            )
            self.added.add(person.id)
        await session.flush()

        # No relationships are mapped, so rows go in by phase: applications, then what refers
        # to them, then what refers to interviews.
        self.screens, self.results = [], []
        for application in applications:
            entry = await credits.consume(
                session, self.workspace_id, pipeline.id, application_id=application.id
            )
            row = Application(
                id=application.id,
                workspace_id=self.workspace_id,
                pipeline_id=pipeline.id,
                candidate_id=application.candidate.id,
                source=application.source,
                resume_path=f"resumes/{self.workspace_id}/{application.id}/resume.pdf",
                resume_filename="resume.pdf",
                resume_pages=self.rng.randint(1, 3),
                resume_bytes=self.rng.randint(60_000, 400_000),
                consent_version="apply@v1",
                consent_at=application.applied_at,
                credit_ledger_id=entry.id,
                applied_at=application.applied_at,
                stage_changed_at=application.applied_at,
            )
            session.add(row)
            self._progress(pipeline, row, application, now=now, zone=zone)
        await session.flush()
        session.add_all(self.screens)
        await session.flush()
        session.add_all(self.results)
        await session.flush()

    def _must_haves(self, must_haves: list[str], passed: bool) -> list[dict[str, Any]]:
        """Every must-have met for a passed screen; one or two missing otherwise."""
        missing = set()
        if not passed and must_haves:
            count = min(len(must_haves), self.detail_rng.randint(1, 2))
            missing = set(self.detail_rng.sample(range(len(must_haves)), count))
        return [
            {
                "criterion": name,
                "met": index not in missing,
                "evidence": "",
                "strength": 0 if index in missing else self.detail_rng.randint(2, 3),
                "waived": False,
                "note": "",
            }
            for index, name in enumerate(must_haves)
        ]

    def _criteria(self, score: int) -> dict[str, Any]:
        """Criterion scores around the overall score, so the strongest area varies."""
        return {
            name: {"score": max(0, min(100, score + self.detail_rng.randint(-9, 9)))}
            for name in ("technical", "communication", "culture")
        }

    def _progress(
        self,
        pipeline: Pipeline,
        row: Application,
        application: SampleApplication,
        *,
        now: datetime,
        zone: ZoneInfo,
    ) -> None:
        """Moves one application along: screen, interview link, interview, score."""
        rng = self.rng
        applied = application.applied_at
        showcase = next((s for s in SHOWCASE if s[0] == application.candidate.full_name), None)
        if showcase is None and now - applied < timedelta(minutes=90):
            return  # still being screened
        screened = applied + timedelta(minutes=rng.randint(3, 9))
        passed = showcase is not None or rng.random() < RESUME_PASS_RATE
        fit = rng.randint(62, 95) if passed else rng.randint(28, 59)
        row.resume_status = "done"
        self.screens.append(
            ResumeAssessment(
                application_id=row.id,
                workspace_id=self.workspace_id,
                score=fit,
                breakdown={},
                must_have_results=self._must_haves(pipeline.must_haves, passed),
                pass_bar=pipeline.resume_pass_bar,
                passed=passed,
                model="sample",
                prompt_version="sample",
                screened_at=screened,
                duration_ms=int((screened - applied).total_seconds() * 1000),
            )
        )
        if not passed:
            self._move(row, "resume_not_match", screened)
            return
        plan = InterviewPlan(
            application_id=row.id,
            workspace_id=self.workspace_id,
            topics=[],
            source="fallback",
            model="none",
            prompt_version="interview_plan_fallback@v1",
            created_at=screened,
        )
        self.screens.append(plan)
        invited = screened + timedelta(minutes=1)
        expires = end_of_day_after(invited, pipeline.link_expiry_days, zone)
        interview = Interview(
            id=uuid.uuid4(),
            workspace_id=self.workspace_id,
            application_id=row.id,
            token_hash=hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
            format=pipeline.interview_format or "video_voice",
            invited_at=invited,
            expires_at=expires,
        )
        self.screens.append(interview)
        self._move(row, "invited", invited)

        outcome = rng.random()
        if showcase is not None:
            outcome = 0.0
        started = invited + timedelta(hours=2 if showcase else rng.uniform(1, 60))
        if outcome < LEAVE and started < min(expires, now):
            interview.started_at = interview.consent_at = started
            interview.consent_version = "interview@v1"
            self._move(row, "interview_in_progress", started)
        if outcome < FINISH:
            minutes = rng.randint(16, 30)
            # Bea Garcia's sample interview (frame CandidateProfile) runs the full 30 minutes.
            if showcase is not None and showcase[0] == "Bea Garcia":
                minutes = 30
            finished = started + timedelta(minutes=minutes)
            if started >= min(expires, now):
                self._expire(interview, "link_expired", expires, now)
            elif finished > now:
                interview.status = "in_progress"
            else:
                self._finish(pipeline, row, interview, plan, finished, showcase, now)
        elif outcome < LEAVE:
            if interview.started_at is None:
                self._expire(interview, "link_expired", expires, now)
            else:
                interview.status = "abandoned"
                interview.drop_reason = "left_unfinished"
                interview.talk_seconds = rng.randint(120, 900)
                if expires < now:
                    interview.status = "expired"
        elif outcome < TECHNICAL:
            interview.drop_reason = "technical_issue"
            if expires < now:
                interview.status = "expired"
        else:
            self._expire(interview, "link_expired", expires, now)

    def _finish(
        self,
        pipeline: Pipeline,
        row: Application,
        interview: Interview,
        plan: InterviewPlan,
        finished: datetime,
        showcase: tuple[str, int, str | None] | None,
        now: datetime,
    ) -> None:
        rng = self.rng
        interview.status = "completed"
        interview.completed_at = finished
        interview.talk_seconds = interview.duration_seconds = int(
            (finished - (interview.started_at or finished)).total_seconds()
        )
        interview.recording_status = "ready"
        interview.recording_path = recording_file_path(
            self.workspace_id, interview.id, "recording.webm"
        )
        self._move(row, "scoring", finished)
        if now - finished < timedelta(minutes=10):
            interview.transcript_status = "processing"
            return
        assessed = finished + timedelta(minutes=rng.randint(3, 8))
        interview.transcript_status = "ready"
        interview.transcribed_at = assessed
        interview.assessment_status = "ready"
        interview.integrity_status = "ready" if pipeline.integrity_enabled else "off"
        interview.integrity_checked_at = assessed if pipeline.integrity_enabled else None
        score = showcase[1] if showcase else max(30, min(89, round(rng.gauss(60, 12))))
        passed = score >= pipeline.pass_mark
        fit = ("strong_fit" if score >= 80 else "good_fit") if passed else None
        criteria = self._criteria(score)
        weights = {
            "technical": pipeline.weight_technical,
            "communication": pipeline.weight_communication,
            "culture": pipeline.weight_culture,
        }
        # Shift the criteria so their weighted sum rounds to the overall score, as scoring does.
        weighted = sum(criteria[name]["score"] * weights[name] for name in weights) / 100
        shift = round(score - weighted)
        for name in criteria:
            criteria[name]["score"] = max(0, min(100, criteria[name]["score"] + shift))
        heaviest = max(weights, key=lambda name: weights[name])
        for _ in range(10):
            total = sum(criteria[name]["score"] * weights[name] for name in weights) / 100
            gap = score - int(Decimal(str(total)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            if gap == 0:
                break
            value = criteria[heaviest]["score"] + (1 if gap > 0 else -1)
            criteria[heaviest]["score"] = max(0, min(100, value))
        if showcase is not None and showcase[0] == "Bea Garcia":
            content = bea_garcia(weights, list(pipeline.skills_to_probe))
        else:
            content = sample_interview(
                self.content_rng,
                score=score,
                scores={name: row["score"] for name, row in criteria.items()},
                weights=weights,
                skills=list(pipeline.skills_to_probe),
                seconds=interview.duration_seconds or 0,
                video=interview.format == "video_voice",
                consent=self.content_rng.random() < 0.9,
                integrity=pipeline.integrity_enabled,
            )
        plan.topics = content.plan_topics
        if content.integrity_checks and pipeline.integrity_enabled:
            interview.integrity_checks = content.integrity_checks
            if interview.integrity_checks.get("face") == "ran":
                interview.biometric_consent_version = "biometric@v1"
        self.results.append(
            Assessment(
                workspace_id=self.workspace_id,
                application_id=row.id,
                interview_id=interview.id,
                overall_score=score,
                criteria=content.criteria,
                topics=content.topics,
                summary=content.summary,
                strengths=content.strengths,
                probes=content.probes,
                answer_stats=content.answer_stats,
                rubric_snapshot={
                    "weight_technical": pipeline.weight_technical,
                    "weight_communication": pipeline.weight_communication,
                    "weight_culture": pipeline.weight_culture,
                    "pass_mark": pipeline.pass_mark,
                },
                passed=passed,
                fit=fit,
                model="sample",
                prompt_version="sample",
                created_at=assessed,
            )
        )
        row.overall_score = score
        row.fit = {"strong_fit": "strong", "good_fit": "good"}.get(fit or "")
        self._move(row, "ready_for_review" if passed else "did_not_pass", assessed)

        flag = showcase[2] if showcase else None
        if flag is None and showcase is None and rng.random() < FLAGGED:
            flag = rng.choice(("second_voice", "read_aloud", "unusual_timing", "no_face"))
        if flag and pipeline.integrity_enabled:
            start = rng.randint(60, 900) * 1000
            self.results.append(
                IntegrityFlag(
                    workspace_id=self.workspace_id,
                    interview_id=interview.id,
                    application_id=row.id,
                    type=flag,
                    start_ms=start,
                    end_ms=start + rng.randint(5, 150) * 1000,
                    confidence=round(rng.uniform(0.62, 0.95), 2),
                    created_at=assessed,
                )
            )
            row.has_open_flags = True
            return
        if passed and showcase is None and now - assessed > timedelta(days=3):
            decided = assessed + timedelta(days=rng.uniform(1, 3))
            pick = rng.random()
            if pick < ADVANCED:
                self._move(row, "advanced", decided)
                row.advanced_at = decided
            elif pick < REJECTED:
                self._move(row, "rejected", decided)
                row.rejected_at = decided
                row.rejected_reason = "Another candidate was a closer match for the team."

    @staticmethod
    def _expire(interview: Interview, reason: str, expires: datetime, now: datetime) -> None:
        if expires < now:
            interview.status = "expired"
            interview.drop_reason = reason

    @staticmethod
    def _move(row: Application, stage: str, at: datetime) -> None:
        row.stage = stage
        row.stage_changed_at = at
