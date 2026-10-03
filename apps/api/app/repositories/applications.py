"""Candidates and their applications in one workspace (MULTI_TENANCY.md §2).

A candidate request names a pipeline by ID; `candidate_pipeline()` finds the workspace it belongs
to (published pipelines only), and everything after that goes through the workspace-scoped
repository below, matched on the candidate's own auth user, so a candidate only ever reaches
their own rows.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import case, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Application, Candidate, Pipeline
from app.repositories.base import WorkspaceRepository

# Pipelines a candidate can reach by ID: published and not cancelled (the apply page's 404s).
CANDIDATE_VISIBLE_STATUSES = ("scheduled", "live", "paused", "paused_no_credits", "closed")


@dataclass(frozen=True)
class CandidatePipeline:
    id: uuid.UUID
    workspace_id: uuid.UUID
    status: str


async def candidate_pipeline(
    session: AsyncSession, pipeline_id: uuid.UUID
) -> CandidatePipeline | None:
    row = (
        await session.execute(
            select(Pipeline.id, Pipeline.workspace_id, Pipeline.status).where(
                Pipeline.id == pipeline_id, Pipeline.status.in_(CANDIDATE_VISIBLE_STATUSES)
            )
        )
    ).one_or_none()
    return CandidatePipeline(*row) if row else None


@dataclass(frozen=True)
class EmailRecipient:
    """What a candidate email needs about its application (MSG-003)."""

    application_id: uuid.UUID
    stage: str
    email: str
    full_name: str
    job_title: str


async def mark_email_undeliverable(
    session: AsyncSession, application_id: uuid.UUID, email: str, now: datetime
) -> bool:
    """A hard bounce (MSG-003): marks the application's candidate while they still have the
    address that bounced. Found by application ID across workspaces, like the webhook's email."""
    candidate_id = (
        select(Application.candidate_id).where(Application.id == application_id).scalar_subquery()
    )
    result = await session.execute(
        update(Candidate)
        .where(
            Candidate.id == candidate_id,
            func.lower(Candidate.email) == email.lower(),
            Candidate.email_undeliverable_at.is_(None),
        )
        .values(email_undeliverable_at=now)
        .returning(Candidate.id)
    )
    return result.first() is not None


@dataclass(frozen=True)
class CandidateDetails:
    email: str
    full_name: str
    phone_country_code: str
    phone: str
    city: str | None
    profile_url: str | None


class ApplicationRepository(WorkspaceRepository[Application]):
    model = Application

    async def find_for_candidate(
        self, pipeline_id: uuid.UUID, auth_user_id: uuid.UUID
    ) -> Application | None:
        """The candidate's application to this pipeline, if they have one."""
        row: Application | None = await self.session.scalar(
            self._scoped()
            .join(
                Candidate,
                (Candidate.workspace_id == Application.workspace_id)
                & (Candidate.id == Application.candidate_id),
            )
            .where(
                Application.pipeline_id == pipeline_id,
                Candidate.auth_user_id == auth_user_id,
                Candidate.deleted_at.is_(None),
            )
        )
        return row

    async def upsert_candidate(
        self, auth_user_id: uuid.UUID, details: CandidateDetails, *, now: datetime
    ) -> uuid.UUID:
        """The candidate row for this person in this workspace, created on their first
        application. Later applications keep the details they sent last."""
        values = {
            "email": details.email,
            "full_name": details.full_name,
            "phone_country_code": details.phone_country_code,
            "phone": details.phone,
            "city": details.city,
            "profile_url": details.profile_url,
            "last_activity_at": now,
        }
        statement = insert(Candidate).values(
            workspace_id=self.workspace_id,
            auth_user_id=auth_user_id,
            first_applied_at=now,
            **values,
        )
        # A new address may work where the old one bounced.
        undeliverable = case(
            (Candidate.email == statement.excluded.email, Candidate.email_undeliverable_at),
            else_=None,
        )
        upsert = statement.on_conflict_do_update(
            constraint="candidates_workspace_id_auth_user_id_key",
            set_={**values, "email_undeliverable_at": undeliverable},
        ).returning(Candidate.id)
        candidate_id: uuid.UUID = (await self.session.execute(upsert)).scalar_one()
        return candidate_id

    def add(self, application: Application) -> Application:
        if application.workspace_id != self.workspace_id:
            raise ValueError("application belongs to another workspace")
        self.session.add(application)
        return application

    async def email_recipient(self, application_id: uuid.UUID) -> EmailRecipient | None:
        """The candidate, job title and workspace time zone for a candidate email. Deleted
        candidates get no email."""
        row = (
            await self.session.execute(
                select(
                    Application.id,
                    Application.stage,
                    Candidate.email,
                    Candidate.full_name,
                    Pipeline.title,
                )
                .join(
                    Candidate,
                    (Candidate.workspace_id == Application.workspace_id)
                    & (Candidate.id == Application.candidate_id),
                )
                .join(
                    Pipeline,
                    (Pipeline.workspace_id == Application.workspace_id)
                    & (Pipeline.id == Application.pipeline_id),
                )
                .where(
                    Application.workspace_id == self.workspace_id,
                    Application.id == application_id,
                    Candidate.deleted_at.is_(None),
                )
            )
        ).one_or_none()
        if row is None:
            return None
        return EmailRecipient(
            application_id=row[0],
            stage=row[1],
            email=row[2],
            full_name=row[3],
            job_title=row[4] or "",
        )

    async def set_stage(self, application_id: uuid.UUID, stage: str, now: datetime) -> str | None:
        """Moves the application to `stage`; returns the stage it was in (None if not found)."""
        previous = await self.session.scalar(
            self._scoped(select(Application.stage))
            .where(Application.id == application_id)
            .with_for_update()
        )
        if previous is None:
            return None
        if previous != stage:
            await self.session.execute(
                update(Application)
                .where(
                    Application.workspace_id == self.workspace_id, Application.id == application_id
                )
                .values(stage=stage, stage_changed_at=now)
            )
        return str(previous)
