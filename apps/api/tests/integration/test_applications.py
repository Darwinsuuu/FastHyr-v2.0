"""APPLY-003: applying uses one credit, once per candidate per pipeline, and the last credit goes
to exactly one applicant. Driven through the API with real Google-style candidate sessions, real
Storage uploads and the credit service."""

import asyncio
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx2
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.context import CandidateContext, Role
from app.core.errors import PipelineNotAcceptingError
from app.integrations.storage import Bucket, SupabaseStorage
from app.jobs.queue import JobQueue
from app.main import create_app
from app.schemas.applications import SubmitApplicationRequest
from app.services import applications, consents, credits
from tests.integration.test_pipelines import admin, db_run, grant, ok, pipeline_in, sql
from tests.pdf_fixtures import plain_pdf
from tests.tenancy.harness import Tenancy, _auth_admin_headers

PASSWORD = "candidate-password-1"


class RecordingQueue(JobQueue):
    """Records what would be queued instead of talking to Redis."""

    def __init__(self) -> None:
        super().__init__("redis://unused")
        self.enqueued: list[tuple[str, tuple[Any, ...]]] = []

    async def enqueue(self, function: str, *args: Any, **kwargs: Any) -> bool:
        self.enqueued.append((function, args))
        return True


@dataclass(frozen=True)
class CandidateUser:
    user_id: uuid.UUID
    email: str
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


@pytest.fixture
def queue() -> RecordingQueue:
    return RecordingQueue()


@pytest.fixture
def tenancy_app(storage: SupabaseStorage, queue: RecordingQueue) -> FastAPI:
    return create_app(storage=storage, job_queue=queue)


@pytest.fixture
def candidates(tenancy: Tenancy) -> Iterator[list[CandidateUser]]:
    """Three candidates signed in as Google accounts (ADR-014). A password stands in for the
    Google round trip; the session still says the account is a Google one."""
    supabase = tenancy.supabase
    made: list[CandidateUser] = []
    try:
        for _ in range(3):
            email = f"candidate-{uuid.uuid4().hex[:8]}@example.com"
            created = httpx2.post(
                f"{supabase.url}/auth/v1/admin/users",
                headers=_auth_admin_headers(supabase),
                json={
                    "email": email,
                    "password": PASSWORD,
                    "email_confirm": True,
                    "app_metadata": {"provider": "google", "providers": ["google"]},
                    "user_metadata": {"full_name": "Paolo Reyes"},
                },
            )
            assert created.status_code == 200, created.text
            signed_in = httpx2.post(
                f"{supabase.url}/auth/v1/token?grant_type=password",
                headers={"apikey": supabase.anon_key},
                json={"email": email, "password": PASSWORD},
            )
            assert signed_in.status_code == 200, signed_in.text
            made.append(
                CandidateUser(
                    uuid.UUID(created.json()["id"]), email, signed_in.json()["access_token"]
                )
            )
        yield made
    finally:
        for candidate in made:
            httpx2.delete(
                f"{supabase.url}/auth/v1/admin/users/{candidate.user_id}",
                headers=_auth_admin_headers(supabase),
            )


@pytest.fixture(autouse=True)
def clean_resumes(tenancy: Tenancy, storage: SupabaseStorage) -> Iterator[None]:
    yield

    async def clean() -> None:
        for workspace in tenancy.workspaces.values():
            for prefix in (str(workspace.id), f"tmp/{workspace.id}"):
                paths = [obj.path for obj in await storage.list(Bucket.RESUMES, prefix)]
                if paths:
                    await storage.delete(Bucket.RESUMES, paths)

    asyncio.run(clean())


def upload(tenancy: Tenancy, candidate: CandidateUser, pipeline_id: str, data: bytes) -> str:
    client = tenancy.anonymous()
    target = ok(
        client.post(
            f"/v1/candidate/pipelines/{pipeline_id}/resume-upload", headers=candidate.headers
        )
    )
    # What the browser does with the signed URL.
    put = httpx2.put(target["url"], content=data, headers={"Content-Type": "application/pdf"})
    assert put.status_code == 200, put.text
    upload_id: str = target["upload_id"]
    return upload_id


def form(pipeline_id: str, upload_id: str, **changes: Any) -> dict[str, Any]:
    return {
        "pipeline_id": pipeline_id,
        "upload_id": upload_id,
        "resume_filename": "paolo-reyes-resume.pdf",
        "full_name": "Paolo Reyes",
        "phone_country_code": "+63",
        "phone": "917 123 4567",
        "city": "Quezon City",
        "profile_url": "https://www.linkedin.com/in/example",
        "consent_notice_id": consents.current("apply").id,
        "source": "linkedin",
        **changes,
    }


def apply(
    tenancy: Tenancy, candidate: CandidateUser, pipeline_id: str, **changes: Any
) -> httpx2.Response:
    upload_id = upload(tenancy, candidate, pipeline_id, plain_pdf(pages=2))
    return tenancy.anonymous().post(
        "/v1/candidate/applications",
        json=form(pipeline_id, upload_id, **changes),
        headers=candidate.headers,
    )


def pipeline_credits(tenancy: Tenancy, pipeline_id: str) -> tuple[str, int, int]:
    row = sql(
        tenancy,
        "select status, credits_used, credits_reserved from pipelines where id = $1",
        uuid.UUID(pipeline_id),
    )[0]
    return row["status"], row["credits_used"], row["credits_reserved"]


def stored(storage: SupabaseStorage, path: str) -> bool:
    return asyncio.run(storage.info(Bucket.RESUMES, path)) is not None


def test_applying_uses_one_credit_linked_to_the_application(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    queue: RecordingQueue,
) -> None:
    grant(tenancy)
    pipeline = pipeline_in(tenancy, "live")
    candidate = candidates[0]
    url = f"/v1/candidate/pipelines/{pipeline['id']}/my-application"
    assert ok(tenancy.anonymous().get(url, headers=candidate.headers)) == {
        "applied_at": None,
        "status": None,
        "workspace_member": False,
    }

    body = ok(apply(tenancy, candidate, pipeline["id"]), 201)
    assert body["created"] is True

    application = sql(
        tenancy, "select * from applications where id = $1", uuid.UUID(body["application_id"])
    )[0]
    assert application["stage"] == "processing_resume"
    assert application["resume_status"] == "pending"
    assert application["source"] == "linkedin"
    assert application["consent_version"] == "apply@v1"
    assert application["resume_pages"] == 2
    assert application["consent_ip_hash"] and "." not in application["consent_ip_hash"]
    assert stored(storage, application["resume_path"])

    ledger = sql(
        tenancy, "select * from credit_ledger where id = $1", application["credit_ledger_id"]
    )[0]
    assert (ledger["kind"], ledger["amount"]) == ("consume", -1)
    assert ledger["application_id"] == application["id"]
    assert pipeline_credits(tenancy, pipeline["id"])[1] == 1

    person = sql(tenancy, "select * from candidates where id = $1", application["candidate_id"])[0]
    assert (person["email"], person["phone"]) == (candidate.email, "9171234567")
    assert person["auth_user_id"] == candidate.user_id

    assert queue.enqueued == [("screen_resume", (application["id"],))]
    applied = ok(tenancy.anonymous().get(url, headers=candidate.headers))
    assert applied["applied_at"] is not None


def test_one_application_per_candidate_per_pipeline(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    grant(tenancy)
    pipeline = pipeline_in(tenancy, "live")
    first = ok(apply(tenancy, candidates[0], pipeline["id"]), 201)

    again = ok(apply(tenancy, candidates[0], pipeline["id"], full_name="Paolo R."), 200)
    assert again == {**first, "created": False}
    assert pipeline_credits(tenancy, pipeline["id"])[1] == 1
    rows = sql(
        tenancy,
        "select count(*) from applications where pipeline_id = $1",
        uuid.UUID(pipeline["id"]),
    )
    assert rows[0]["count"] == 1


def test_only_one_applicant_gets_the_last_credit(
    tenancy: Tenancy, candidates: list[CandidateUser], storage: SupabaseStorage
) -> None:
    grant(tenancy)
    pipeline = pipeline_in(tenancy, "live")
    pipeline_id = uuid.UUID(pipeline["id"])
    workspace_id = tenancy.workspace("a").id

    async def use_all_but_one(session: AsyncSession) -> None:
        for _ in range(pipeline["credits_reserved"] - 1):
            await credits.consume(session, workspace_id, pipeline_id)
        await session.commit()

    db_run(tenancy, use_all_but_one)
    racers = candidates[:2]
    uploads = [upload(tenancy, racer, pipeline["id"], plain_pdf()) for racer in racers]

    async def race() -> list[Any]:
        url = tenancy.supabase.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        engine = create_async_engine(url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)

        async def submit(racer: CandidateUser, upload_id: str) -> Any:
            async with sessions() as session:
                return await applications.submit(
                    session,
                    CandidateContext(user_id=racer.user_id, email=racer.email),
                    storage,
                    RecordingQueue(),
                    SubmitApplicationRequest(**form(pipeline["id"], upload_id)),
                    client_ip="203.0.113.7",
                    ip_hash_key="test",
                )

        try:
            return await asyncio.gather(
                *(
                    submit(racer, upload_id)
                    for racer, upload_id in zip(racers, uploads, strict=True)
                ),
                return_exceptions=True,
            )
        finally:
            await engine.dispose()

    results = asyncio.run(race())
    won = [result for result in results if not isinstance(result, BaseException)]
    lost = [result for result in results if isinstance(result, BaseException)]
    assert len(won) == 1 and won[0].created
    assert len(lost) == 1 and isinstance(lost[0], PipelineNotAcceptingError)

    status, used, reserved = pipeline_credits(tenancy, pipeline["id"])
    assert used == reserved and status == "paused_no_credits"
    consumed = sql(
        tenancy,
        "select count(*) from credit_ledger where pipeline_id = $1 and kind = 'consume'",
        pipeline_id,
    )
    assert consumed[0]["count"] == reserved
    # The loser keeps nothing: no application, no candidate row, no stored résumé.
    rows = sql(tenancy, "select candidate_id from applications where pipeline_id = $1", pipeline_id)
    assert len(rows) == 1
    people = sql(tenancy, "select count(*) from candidates where workspace_id = $1", workspace_id)
    assert people[0]["count"] == 1
    files = asyncio.run(storage.list(Bucket.RESUMES, str(workspace_id)))
    assert len(files) == 1


def test_a_bad_file_uses_no_credit(tenancy: Tenancy, candidates: list[CandidateUser]) -> None:
    grant(tenancy)
    pipeline = pipeline_in(tenancy, "live")
    upload_id = upload(tenancy, candidates[0], pipeline["id"], b"not a pdf at all")
    response = tenancy.anonymous().post(
        "/v1/candidate/applications",
        json=form(pipeline["id"], upload_id),
        headers=candidates[0].headers,
    )
    assert response.status_code == 422
    assert response.json()["code"] == "pdf_not_pdf"
    assert pipeline_credits(tenancy, pipeline["id"])[1] == 0


def test_applying_needs_a_live_pipeline(tenancy: Tenancy, candidates: list[CandidateUser]) -> None:
    grant(tenancy)
    headers = candidates[0].headers
    paused = pipeline_in(tenancy, "paused")
    response = tenancy.anonymous().post(
        f"/v1/candidate/pipelines/{paused['id']}/resume-upload", headers=headers
    )
    assert response.status_code == 409
    assert response.json()["code"] == "pipeline_not_accepting"

    draft = pipeline_in(tenancy, "draft")
    for url in (
        f"/v1/candidate/pipelines/{draft['id']}/resume-upload",
        f"/v1/candidate/pipelines/{uuid.uuid4()}/resume-upload",
    ):
        assert tenancy.anonymous().post(url, headers=headers).status_code == 404


def test_candidate_routes_need_a_google_or_microsoft_session(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    grant(tenancy)
    pipeline = pipeline_in(tenancy, "live")
    # A TA member's email + password session is not a candidate session (ADR-014).
    member = tenancy.member("a", Role.RECRUITER)
    response = tenancy.anonymous().post(
        f"/v1/candidate/pipelines/{pipeline['id']}/resume-upload",
        headers={"Authorization": f"Bearer {member.access_token}"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "candidate_sign_in_required"
    assert (
        tenancy.anonymous()
        .post(f"/v1/candidate/pipelines/{pipeline['id']}/resume-upload")
        .status_code
        == 401
    )


@pytest.mark.parametrize("action", ["pause", "close"])
def test_a_pipeline_that_stops_after_the_upload_uses_no_credit(
    tenancy: Tenancy, candidates: list[CandidateUser], storage: SupabaseStorage, action: str
) -> None:
    """APPLY-004: the page loaded and the résumé uploaded while the pipeline was live, then the
    TA team paused or closed it before the candidate pressed Send."""
    grant(tenancy)
    pipeline = pipeline_in(tenancy, "live")
    upload_id = upload(tenancy, candidates[0], pipeline["id"], plain_pdf())
    ok(admin(tenancy).post(f"/v1/pipelines/{pipeline['id']}/{action}"))

    response = tenancy.anonymous().post(
        "/v1/candidate/applications",
        json=form(pipeline["id"], upload_id),
        headers=candidates[0].headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "pipeline_not_accepting"
    pipeline_id = uuid.UUID(pipeline["id"])
    consumed = sql(
        tenancy,
        "select count(*) from credit_ledger where pipeline_id = $1 and kind = 'consume'",
        pipeline_id,
    )
    assert consumed[0]["count"] == 0
    rows = sql(tenancy, "select count(*) from applications where pipeline_id = $1", pipeline_id)
    assert rows[0]["count"] == 0
    workspace_id = tenancy.workspace("a").id
    assert asyncio.run(storage.list(Bucket.RESUMES, str(workspace_id))) == []


def test_my_application_shows_status_words_never_the_stage(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    grant(tenancy)
    pipeline = pipeline_in(tenancy, "live")
    candidate = candidates[0]
    url = f"/v1/candidate/pipelines/{pipeline['id']}/my-application"
    application_id = uuid.UUID(ok(apply(tenancy, candidate, pipeline["id"]), 201)["application_id"])

    seen = {}
    for stage in ("processing_resume", "invited", "resume_not_match", "rejected", "advanced"):
        sql(tenancy, "update applications set stage = $1 where id = $2", stage, application_id)
        seen[stage] = ok(tenancy.anonymous().get(url, headers=candidate.headers))["status"]
    assert seen == {
        "processing_resume": "received",
        "invited": "interview",
        # Decisions reach candidates by email, some days later; the page never gets ahead.
        "resume_not_match": "with_team",
        "rejected": "with_team",
        "advanced": "with_team",
    }


def test_a_workspace_member_can_apply_and_is_told_so(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    """A TA member signed in with Google may apply to their own workspace's pipeline; the form
    warns them (APPLY-004). Another workspace's membership doesn't count."""
    grant(tenancy)
    pipeline = pipeline_in(tenancy, "live")
    member, outsider = candidates[0], candidates[1]
    membership = uuid.uuid4()
    sql(
        tenancy,
        "insert into workspace_members (id, workspace_id, user_id, role) values ($1, $2, $3, $4)",
        membership,
        tenancy.workspace("a").id,
        member.user_id,
        "recruiter",
    )
    try:
        url = f"/v1/candidate/pipelines/{pipeline['id']}/my-application"
        mine = ok(tenancy.anonymous().get(url, headers=member.headers))
        assert mine == {"applied_at": None, "status": None, "workspace_member": True}
        assert not ok(tenancy.anonymous().get(url, headers=outsider.headers))["workspace_member"]

        ok(apply(tenancy, member, pipeline["id"]), 201)
        assert ok(tenancy.anonymous().get(url, headers=member.headers))["status"] == "received"
    finally:
        sql(tenancy, "delete from workspace_members where id = $1", membership)
