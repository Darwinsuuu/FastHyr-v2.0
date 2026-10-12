"""ASMT-001: a transcribed interview is scored in the real worker. A pass moves the candidate to
`ready_for_review`; a fail moves them to `did_not_pass` with `reject_interview` scheduled 3
business days after the interview, carrying a human-review link, unless the pipeline turned
post-interview emails off. Scores without evidence are never used, the model never sees the
candidate's name, repeats change nothing and the sweeper picks up a lost job."""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import fakes
from app.ai.prompts import Prompt
from app.ai.schemas.interview_assessment import InterviewAssessment
from app.jobs.queue import JobQueue
from app.services import candidate_emails, scoring
from tests.integration.test_applications import CandidateUser, candidates, clean_resumes, queue
from tests.integration.test_emails import FakeSender
from tests.integration.test_interview_sessions import interview, ready, realtime, tenancy_app
from tests.integration.test_pipelines import db_run, sql
from tests.integration.test_post_screen import owner_sql, sha256, sweep, token_in
from tests.integration.worker import drain
from tests.tenancy.harness import Tenancy

__all__ = ["candidates", "clean_resumes", "queue", "realtime", "tenancy_app"]

# start s, end s, speaker, text, topic (the plan in test_interview_sessions.TOPICS)
LINES = [
    (0, 5, "interviewer", "Hi, thanks for joining. Tell me about your current role.", 0),
    (6, 14, "candidate", "I'm Paolo Reyes. I build the payments API at a fintech.", 0),
    (15, 19, "interviewer", "How did you design the payments API?", 1),
    (21, 35, "candidate", "We kept every endpoint idempotent with request keys.", 1),
    (36, 38, "other", "Is that the interviewer?", 1),
    (39, 42, "interviewer", "Walk me through a hard bug.", 2),
    (44, 58, "candidate", "A race in the ledger writes; we added row locks and a retry.", 2),
    (59, 62, "interviewer", "What would you like to know?", 3),
    (64, 68, "candidate", "How does the team share on-call?", 3),
]


class ScoringAI:
    """Answers `interview_assessment@v1` with the AI_FAKE answer, `change(answer)` applied."""

    model = "stub"

    def __init__(self, change: Any = None) -> None:
        self.change = change
        self.seen: list[dict[str, str]] = []

    async def structured[T: BaseModel](
        self,
        *,
        purpose: str,
        prompt: Prompt,
        variables: dict[str, str],
        schema: type[T],
        workspace_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
        temperature: float | None = None,
    ) -> T:
        assert schema is InterviewAssessment
        self.seen.append(variables)
        answer = fakes.interview_assessment(variables)
        if self.change:
            self.change(answer)
        return schema.model_validate(answer)


def low(answer: dict[str, Any]) -> None:
    for criterion in answer["criteria"].values():
        criterion["score"] = 40


def invented(answer: dict[str, Any]) -> None:
    for criterion in answer["criteria"].values():
        for item in criterion["evidence"]:
            item["quote"] = "I single-handedly rebuilt the whole platform"


@pytest.fixture
def queue_name() -> str:
    return f"arq:test:{uuid.uuid4().hex[:12]}"


def transcribed(
    tenancy: Tenancy, candidate: CandidateUser, *, ago: timedelta = timedelta(0)
) -> uuid.UUID:
    """A completed interview `ago` in the past with its transcript ready; the application is in
    `scoring`, as INTV-004 and INTV-008 leave it."""
    _, interview_id = ready(tenancy, candidate)
    completed = datetime.now(UTC) - ago
    sql(
        tenancy,
        "update interviews set status = 'completed', started_at = $2, completed_at = $3, "
        "recording_status = 'ready', transcript_status = 'ready', transcribed_at = $3 "
        "where id = $1",
        interview_id,
        completed - timedelta(minutes=20),
        completed,
    )
    sql(
        tenancy,
        "update applications set stage = 'scoring' "
        "where id = (select application_id from interviews where id = $1)",
        interview_id,
    )
    for seq, (start, end, speaker, text, topic) in enumerate(LINES):
        sql(
            tenancy,
            "insert into transcript_segments (workspace_id, interview_id, seq, start_ms, end_ms, "
            "speaker, text, topic_index) values ($1, $2, $3, $4, $5, $6, $7, $8)",
            tenancy.workspace("a").id,
            interview_id,
            seq,
            start * 1000,
            end * 1000,
            speaker,
            text,
            topic,
        )
    return interview_id


def enqueue_score(
    redis_url: str, queue_name: str, workspace_id: uuid.UUID, interview_id: uuid.UUID
) -> None:
    async def main() -> None:
        queue = JobQueue(redis_url, queue_name=queue_name)
        try:
            await queue.enqueue(scoring.SCORE_JOB, workspace_id, interview_id, key=interview_id)
        finally:
            await queue.close()

    asyncio.run(main())


def score(
    tenancy: Tenancy,
    interview_id: uuid.UUID,
    redis_url: str,
    queue_name: str,
    ai: ScoringAI,
    sender: FakeSender | None = None,
) -> None:
    enqueue_score(redis_url, queue_name, tenancy.workspace("a").id, interview_id)
    drain(redis_url, queue_name, ai=ai, email_sender=sender or FakeSender())


def rows(tenancy: Tenancy, table: str, interview_id: uuid.UUID) -> list[dict[str, Any]]:
    """The application's rows, with jsonb columns decoded."""
    found = sql(
        tenancy,
        f"select * from {table} where application_id = "
        "(select application_id from interviews where id = $1)",
        interview_id,
    )
    jsonb = {"criteria", "topics", "summary", "answer_stats", "rubric_snapshot", "output"}
    return [
        {key: json.loads(value) if key in jsonb else value for key, value in row.items()}
        for row in found
    ]


def test_a_passing_interview_is_ready_for_review_with_its_evidence(
    tenancy: Tenancy, candidates: list[CandidateUser], redis_url: str, queue_name: str
) -> None:
    interview_id = transcribed(tenancy, candidates[0])
    ai = ScoringAI()
    score(tenancy, interview_id, redis_url, queue_name, ai)

    row = interview(tenancy, interview_id)
    assert (row["stage"], row["assessment_status"]) == ("ready_for_review", "ready")
    [result] = rows(tenancy, "assessments", interview_id)
    # The fake scores 82 / 78 / 80; the default rubric is 50 / 30 / 20 with pass mark 70.
    [pipeline] = sql(
        tenancy,
        "select p.* from pipelines p join applications a on a.pipeline_id = p.id where a.id = $1",
        result["application_id"],
    )
    weights = [pipeline[f"weight_{name}"] for name in ("technical", "communication", "culture")]
    expected = round((82 * weights[0] + 78 * weights[1] + 80 * weights[2]) / 100)
    assert (result["overall_score"], result["passed"], result["interview_id"]) == (
        expected,
        True,
        interview_id,
    )
    assert result["fit"] in ("strong_fit", "good_fit")
    # The Candidates tab reads the score and badge from the application (PIPE-008).
    [application] = sql(
        tenancy,
        "select overall_score, fit from applications where id = $1",
        result["application_id"],
    )
    assert (application["overall_score"], application["fit"]) == (
        expected,
        result["fit"].removesuffix("_fit"),
    )
    assert result["rubric_snapshot"]["pass_mark"] == pipeline["pass_mark"]
    technical = result["criteria"]["technical"]
    assert technical["evidence"][0] == {
        "source": "interview",
        "quote": "I'm [NAME]. I build the payments API at",
        "start_ms": 6_000,
        "source_label": "Opening",
    }
    assert [topic["title"] for topic in result["topics"]] == [
        "Getting started",
        "API design",
        "Debugging",
        "Your questions",
    ]
    assert result["answer_stats"]["answers"] == 4
    assert result["answer_stats"]["candidate_questions"] == 1

    # The model never saw the candidate's name or the other voice.
    [seen] = ai.seen
    assert "Paolo" not in seen["transcript"] and "Reyes" not in seen["transcript"]
    assert "Is that the interviewer?" not in seen["transcript"]

    [decision] = rows(tenancy, "ai_decisions", interview_id)
    assert (decision["type"], decision["outcome"], decision["score"]) == (
        "interview_score",
        "pass",
        expected,
    )
    assert decision["input_ref"] == f"transcript_segments:{interview_id}"
    assert "Paolo" not in str(decision["output"]) and "payments" not in str(decision["output"])
    assert rows(tenancy, "email_messages", interview_id) == []

    # A repeated job changes nothing.
    score(tenancy, interview_id, redis_url, queue_name, ai)
    assert len(ai.seen) == 1
    assert len(rows(tenancy, "assessments", interview_id)) == 1


def test_a_failed_interview_schedules_a_rejection_with_a_review_link(
    tenancy: Tenancy, candidates: list[CandidateUser], redis_url: str, queue_name: str
) -> None:
    interview_id = transcribed(tenancy, candidates[0])
    sender = FakeSender()
    score(tenancy, interview_id, redis_url, queue_name, ScoringAI(low), sender)

    row = interview(tenancy, interview_id)
    assert row["stage"] == "did_not_pass"
    [result] = rows(tenancy, "assessments", interview_id)
    assert (result["overall_score"], result["passed"], result["fit"]) == (40, False, None)

    async def three_business_days_later(session: AsyncSession) -> datetime:
        return await candidate_emails.send_at(
            session, tenancy.workspace("a").id, row["completed_at"], 3
        )

    due = db_run(tenancy, three_business_days_later)
    [email] = rows(tenancy, "email_messages", interview_id)
    assert (email["template_key"], email["status"], email["scheduled_for"]) == (
        "reject_interview",
        "scheduled",
        due,
    )
    assert email["application_stage"] == "did_not_pass"
    assert sender.sent == []
    [link] = rows(tenancy, "review_links", interview_id)
    assert link["decision_type"] == "interview"
    assert sha256(token_in(email["html_rendered"], "review-request")) == link["token_hash"]
    assert link["expires_at"] == due + timedelta(days=30)


def test_no_rejection_email_when_the_pipeline_turned_it_off(
    tenancy: Tenancy, candidates: list[CandidateUser], redis_url: str, queue_name: str
) -> None:
    interview_id = transcribed(tenancy, candidates[0])
    owner_sql(
        tenancy,
        "update pipelines set email_post_interview = false where id = "
        "(select pipeline_id from applications where id = "
        "(select application_id from interviews where id = $1))",
        interview_id,
    )
    score(tenancy, interview_id, redis_url, queue_name, ScoringAI(low))

    assert interview(tenancy, interview_id)["stage"] == "did_not_pass"
    assert rows(tenancy, "email_messages", interview_id) == []
    assert rows(tenancy, "review_links", interview_id) == []


def test_scores_without_evidence_are_never_used(
    tenancy: Tenancy, candidates: list[CandidateUser], redis_url: str, queue_name: str
) -> None:
    interview_id = transcribed(tenancy, candidates[0])
    ai = ScoringAI(invented)
    score(tenancy, interview_id, redis_url, queue_name, ai)

    # Asked once more, then the job gives up: the application waits in `scoring` for a person.
    assert len(ai.seen) == 2
    row = interview(tenancy, interview_id)
    assert (row["stage"], row["assessment_status"]) == ("scoring", "failed")
    assert rows(tenancy, "assessments", interview_id) == []
    assert rows(tenancy, "ai_decisions", interview_id) == []


def test_a_transcript_without_the_candidate_is_not_scored(
    tenancy: Tenancy, candidates: list[CandidateUser], redis_url: str, queue_name: str
) -> None:
    interview_id = transcribed(tenancy, candidates[0])
    sql(
        tenancy,
        "delete from transcript_segments where speaker = 'candidate' and interview_id = $1",
        interview_id,
    )
    ai = ScoringAI()
    score(tenancy, interview_id, redis_url, queue_name, ai)

    assert ai.seen == []
    row = interview(tenancy, interview_id)
    assert (row["stage"], row["assessment_status"]) == ("scoring", "failed")


def test_a_candidate_who_left_scoring_keeps_their_stage(
    tenancy: Tenancy, candidates: list[CandidateUser], redis_url: str, queue_name: str
) -> None:
    interview_id = transcribed(tenancy, candidates[0])
    sql(
        tenancy,
        "update applications set stage = 'rejected' "
        "where id = (select application_id from interviews where id = $1)",
        interview_id,
    )
    score(tenancy, interview_id, redis_url, queue_name, ScoringAI(low))

    assert interview(tenancy, interview_id)["stage"] == "rejected"
    assert len(rows(tenancy, "assessments", interview_id)) == 1
    assert rows(tenancy, "email_messages", interview_id) == []


def test_sweeper_requeues_transcripts_redis_lost(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    redis_url: str,
    queue_name: str,
) -> None:
    lost = transcribed(tenancy, candidates[0], ago=timedelta(minutes=15))
    recent = transcribed(tenancy, candidates[1])

    assert sweep(redis_url, queue_name) >= 1
    drain(redis_url, queue_name, ai=ScoringAI(), email_sender=FakeSender())

    assert interview(tenancy, lost)["stage"] == "ready_for_review"
    assert interview(tenancy, recent)["stage"] == "scoring"
