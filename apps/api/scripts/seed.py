"""Seed the "Acme Talent" sample workspace from the design (FND-014, DATABASE.md §5).

Run after migrations (`make db-reset` runs it), from apps/api:
    uv run python scripts/seed.py
Connects as the database owner (`SEED_DATABASE_URL`, default: local Supabase) because it writes
`auth.users`. Safe to run twice: it stops when the workspace already exists.

Everyone here is synthetic and uses the reserved `.test` domain. All sample users sign in with
email + password; the local password is printed at the end. Against any other database, set
`SEED_USER_PASSWORD`.

Credits go through `app.services.credits`, so batches, reserves and the ledger add up exactly as
they would in the product. Each epic extends this file as its tables arrive: pipelines have their
full setup, slugs and dates since PIPE-001; the nine default email templates since MSG-001 (the
interview invitation edited by Maria, as in the design); since DASH-003 every credit a pipeline used
is a sample applicant with a screen, an interview and a score (scripts/seed_applications.py), and
two of them asked for a human review (ASMT-008).
"""

import asyncio
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.slugs import slugify
from app.emails.defaults import TemplateKey
from app.models import (
    Application,
    CompanyProfile,
    Department,
    HumanReviewRequest,
    Invite,
    MemberDepartment,
    Pipeline,
    Profile,
    ReviewLink,
    Workspace,
    WorkspaceMember,
)
from app.services import credits, email_templates
from app.services.invites import new_code, new_token_hash
from scripts.seed_applications import ApplicantMaker, SampleApplication

LOCAL_OWNER_DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
LOCAL_PASSWORD = "acme-talent-local"
WORKSPACE_SLUG = "acme-talent"
EMAIL_DOMAIN = "acme-talent.test"
# Stable IDs, so the same sample user keeps its ID across resets.
NAMESPACE = uuid.UUID("6f1c3a52-0f4e-4d8e-9a57-2b8d1c0e7a11")


@dataclass(frozen=True)
class SampleUser:
    key: str
    full_name: str
    role: str
    departments: tuple[str, ...]
    last_active: timedelta | None
    is_owner: bool = False

    @property
    def email(self) -> str:
        return f"{self.key}@{EMAIL_DOMAIN}"

    @property
    def id(self) -> uuid.UUID:
        return uuid.uuid5(NAMESPACE, self.email)


# Frame ManageMembers. The owner stands in for the frame's "(you)" row.
USERS = (
    SampleUser("dana", "Dana Lim", "admin", (), timedelta(minutes=0), is_owner=True),
    SampleUser("maria", "Maria Santos", "recruiter", ("Engineering", "Design"), timedelta(hours=2)),
    SampleUser("jomar", "Jomar Reyes", "hiring_manager", ("Engineering",), timedelta(days=3)),
    SampleUser("angela", "Angela Cruz", "recruiter", ("Customer Support",), timedelta(minutes=5)),
)

# Frame ManageMembers, Pending invites tab: (email, role, days since sent).
INVITES = (
    (f"paolo@{EMAIL_DOMAIN}", "hiring_manager", 2),
    ("recruiter@agency.test", "recruiter", 5),
)

# Frame Departments: (name, description, created).
DEPARTMENTS = (
    ("Engineering", "Backend, frontend, platform, mobile and QA roles", datetime(2026, 1, 12)),
    ("Customer Support", "Support specialists and technical support", datetime(2026, 1, 12)),
    ("Design", "Product design and research", datetime(2026, 2, 3)),
    ("Sales", "SDRs and account executives", datetime(2026, 2, 3)),
    ("Marketing", "Content, growth and brand", datetime(2026, 3, 18)),
    ("Data & Analytics", "Analysts and data engineers", datetime(2026, 5, 2)),
    ("People", "HR, recruiting and people operations", datetime(2026, 5, 2)),
    ("Finance", "Payroll, accounting and FP&A", datetime(2026, 7, 14)),
    ("Operations", "Office and business operations", datetime(2026, 7, 14)),
)


@dataclass(frozen=True)
class SamplePipeline:
    title: str
    department: str | None
    status: str
    reserve: int
    used: int
    used_this_month: int = 0


# Frames PipelinesV2 and CreditUsage, plus a draft and a manually paused pipeline so every status
# appears. `used_this_month` comes from the current plan; the rest came from the credit pack.
PIPELINES = (
    SamplePipeline("Staff Platform Engineer", "Engineering", "paused_no_credits", 34, 34, 7),
    SamplePipeline("Senior Backend Engineer", "Engineering", "live", 250, 142, 38),
    SamplePipeline("Product Designer", "Design", "live", 100, 58, 14),
    SamplePipeline("Customer Support Specialist", "Customer Support", "live", 250, 210, 42),
    SamplePipeline("Sales Development Representative", "Sales", "live", 200, 88, 18),
    SamplePipeline("Frontend Engineer (React)", "Engineering", "live", 150, 73, 16),
    SamplePipeline("Data Analyst", "Data & Analytics", "live", 120, 49, 12),
    SamplePipeline("HR Generalist", "People", "live", 80, 52, 10),
    SamplePipeline("DevOps Engineer", "Engineering", "live", 100, 41, 11),
    SamplePipeline("Content Marketing Specialist", "Marketing", "live", 100, 66, 13),
    SamplePipeline("Technical Support Engineer", "Customer Support", "live", 100, 27, 9),
    SamplePipeline("Recruitment Coordinator", "People", "paused", 40, 12),
    SamplePipeline("UX Researcher", "Design", "scheduled", 60, 0),
    SamplePipeline("Growth Marketing Manager", "Marketing", "scheduled", 80, 0),
    SamplePipeline("Payroll Specialist", "Finance", "scheduled", 40, 0),
    SamplePipeline("Brand Designer", "Design", "draft", 0, 0),
    SamplePipeline("QA Automation Engineer", "Engineering", "closed", 80, 64),
    SamplePipeline("Mobile Engineer (iOS)", "Engineering", "closed", 60, 47),
    # Cancelled before it opened, so nobody applied and its reserve came back.
    SamplePipeline("Account Executive", "Sales", "cancelled", 150, 0),
    SamplePipeline("Office Administrator", None, "closed", 150, 118),
)

# Who owns each department's pipelines: the Recruiter assigned to it, else the owner (Admin).
PIPELINE_OWNERS = {
    "Engineering": "maria",
    "Design": "maria",
    "Customer Support": "angela",
}
# Pipelines closed on their date ("Completed"); the other closed ones were closed by hand.
CLOSED_ON_SCHEDULE = {"QA Automation Engineer", "Office Administrator"}


# A full job description in the shape TA teams paste (headings and bullet lists), so the apply
# page (APPLY-001) has something realistic to show. Other pipelines get a one-line sample.
FULL_JDS = {
    "Senior Backend Engineer": "\n".join(
        (
            (
                "You'll join the platform team at Acme Talent, the group that builds and runs the"
                " services and databases behind our core product."
            ),
            "",
            (
                "This is a senior role with real ownership. You'll take problems from a rough "
                "idea to a running service, make the technical calls along the way, and help the "
                "people around you do their best work."
            ),
            "",
            "What you'll do",
            (
                "- Design, build and run backend services in Go that other teams depend on every "
                "day."
            ),
            "- Keep our PostgreSQL databases fast and reliable as data and traffic grow.",
            (
                "- Own services in production: monitoring, incident response and clear, blameless"
                " reviews."
            ),
            "- Review code, pair with teammates and help newer engineers grow.",
            "",
            "What you'll bring",
            "- Several years building and running backend systems in production.",
            "- Strong experience with Go or Java, and willingness to work mainly in Go.",
            "- Hands-on experience with PostgreSQL or another relational database at scale.",
            "- Clear written and spoken communication in English.",
            "",
            "What we offer",
            "- Competitive pay, reviewed every year.",
            "- HMO coverage for you, with the option to add dependents.",
            "- A yearly learning budget for courses, books and conferences.",
            "- Sample job description for local development.",
        )
    ),
}


def pipeline_setup(sample: SamplePipeline, index: int, now: datetime) -> dict[str, object]:
    """A complete, plausible setup for a sample pipeline, with dates that fit its status."""
    setup: dict[str, object] = {
        "title": sample.title,
        "employment_type": "full_time",
        "work_setup": ("hybrid", "remote", "on_site")[index % 3],
        "location": "Makati City, Metro Manila",
        "jd_text": FULL_JDS.get(
            sample.title,
            f"Acme Talent is hiring a {sample.title} to join a growing team. You'll own your work "
            "end to end, collaborate across teams and help shape how we build. Sample job "
            "description for local development.",
        ),
        "must_haves": ["2+ years in a similar role", "Clear written English", "Team player"],
        "nice_to_haves": ["Startup experience"],
        "open_to": ["career_changers", "returners"],
        "interview_format": "video_voice" if index % 4 else "voice_only",
        "tone": ("warm", "professional", "direct")[index % 3],
        "seniority": ("mid", "senior", "entry", "lead")[index % 4],
        "skills_to_probe": ["Problem solving", "Communication", "Ownership"],
        "weight_technical": 50,
        "weight_communication": 30,
        "weight_culture": 20,
        "credits_to_reserve": max(10, sample.reserve // 10 * 10),
    }
    if sample.status == "draft":
        return {**setup, "open_mode": "now", "skills_to_probe": [], "credits_to_reserve": None}
    duration_days = 60
    if sample.status in {"scheduled", "cancelled"}:
        opens_at = now + timedelta(days=7 * (index % 4 + 1))
        duration_days = 30
        setup["open_mode"] = "scheduled"
    elif sample.status == "closed":
        opens_at = now - timedelta(days=100 + index)
        setup["open_mode"] = "now"
    else:
        opens_at = now - timedelta(days=5 + 3 * index)
        setup["open_mode"] = "now"
    return setup | {
        "duration_days": duration_days,
        "opens_at": opens_at,
        "closes_at": opens_at + timedelta(days=duration_days),
        "slug": slugify(sample.title),
        "published_at": opens_at - timedelta(days=2),
        "locked_at": None if sample.status in {"scheduled", "cancelled"} else opens_at,
    }


def ended_at(sample: SamplePipeline, pipeline: Pipeline, now: datetime) -> datetime:
    """When a sample pipeline closed or was cancelled: on its date when it closed on schedule,
    some weeks before its date when closed by hand, and a few weeks ago when cancelled."""
    if sample.status == "cancelled" or pipeline.closes_at is None:
        return now - timedelta(days=21)
    if sample.title in CLOSED_ON_SCHEDULE:
        return pipeline.closes_at
    return pipeline.closes_at - timedelta(days=12)


PLAN_CREDITS = 300
# Frame CreditUsage: 1,640 available, 110 of them left in the plan, the rest in a credit pack.
EXTRA_LEFT = 1530


def owner_database_url() -> tuple[str, bool]:
    url = os.environ.get("SEED_DATABASE_URL", LOCAL_OWNER_DATABASE_URL)
    local = urlparse(url).hostname in {"127.0.0.1", "localhost"}
    return url.replace("postgresql://", "postgresql+asyncpg://", 1), local


async def add_user(session: AsyncSession, user: SampleUser, password: str) -> None:
    """An email + password account, confirmed, the way Supabase Auth stores one. The
    `on_auth_user_created` trigger adds the profile (name and email)."""
    await session.execute(
        text(
            """
            insert into auth.users (
              instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
              raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
              confirmation_token, recovery_token, email_change_token_new, email_change
            ) values (
              '00000000-0000-0000-0000-000000000000', :id, 'authenticated', 'authenticated',
              :email, extensions.crypt(:password, extensions.gen_salt('bf')), now(),
              '{"provider": "email", "providers": ["email"]}',
              jsonb_build_object('full_name', cast(:name as text)), now(), now(), '', '', '', ''
            ) on conflict (id) do nothing
            """
        ),
        {"id": user.id, "email": user.email, "password": password, "name": user.full_name},
    )
    await session.execute(
        text(
            """
            insert into auth.identities (
              id, user_id, provider_id, provider, identity_data, last_sign_in_at,
              created_at, updated_at
            ) values (
              :id, :id, cast(:sub as text), 'email',
              jsonb_build_object('sub', cast(:sub as text), 'email', cast(:email as text),
                                 'email_verified', true),
              now(), now(), now()
            ) on conflict do nothing
            """
        ),
        {"id": user.id, "sub": str(user.id), "email": user.email},
    )


async def seed(session_factory: async_sessionmaker[AsyncSession], password: str) -> bool:
    now = datetime.now(UTC)
    async with session_factory() as session:
        if await session.scalar(select(Workspace.id).where(Workspace.slug == WORKSPACE_SLUG)):
            return False

        for user in USERS:
            await add_user(session, user, password)
        await session.flush()

        owner = USERS[0]
        created = datetime(2026, 1, 12, 2, 0, tzinfo=UTC)
        workspace = Workspace(
            name="Acme Talent",
            slug=WORKSPACE_SLUG,
            owner_id=owner.id,
            timezone="Asia/Manila",
            trial_granted_at=created,
            created_at=created,
        )
        session.add(workspace)
        await session.flush()
        session.add(
            CompanyProfile(
                workspace_id=workspace.id,
                company_name="Acme Talent",
                website=f"https://{EMAIL_DOMAIN}",
                industry="technology",
                company_size="51-200",
                hq_country="PH",
                timezone="Asia/Manila",
                careers_url=f"https://{EMAIL_DOMAIN}/careers",
                about=(
                    "Acme Talent builds hiring software for growing teams across Southeast "
                    "Asia. Sample company for local development."
                ),
            )
        )

        departments: dict[str, uuid.UUID] = {}
        members: dict[str, uuid.UUID] = {}
        for name, description, created_on in DEPARTMENTS:
            department = Department(
                workspace_id=workspace.id,
                name=name,
                description=description,
                created_at=created_on.replace(tzinfo=UTC),
            )
            session.add(department)
            await session.flush()
            departments[name] = department.id

        for user in USERS:
            member = WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user.id,
                role=user.role,
                is_owner=user.is_owner,
                last_active_at=now - user.last_active if user.last_active is not None else None,
                created_at=created,
            )
            session.add(member)
            await session.flush()
            members[user.key] = member.id
            for name in user.departments:
                session.add(
                    MemberDepartment(
                        workspace_id=workspace.id,
                        member_id=member.id,
                        department_id=departments[name],
                    )
                )
            profile = await session.get(Profile, user.id)
            if profile is not None:
                profile.last_workspace_id = workspace.id

        for email, role, days in INVITES:
            sent = now - timedelta(days=days)
            session.add(
                Invite(
                    workspace_id=workspace.id,
                    email=email,
                    role=role,
                    code=new_code(),
                    token_hash=new_token_hash()[1],
                    invited_by=owner.id,
                    created_at=sent,
                    expires_at=sent + timedelta(days=7),
                )
            )
        await session.commit()

        await seed_credits(session, workspace.id, departments, members, created, now)
        await seed_email_templates(session, workspace.id)
        await seed_review_requests(session, workspace.id, now)
    return True


# Two candidates who asked for a person to review an automated rejection (ASMT-008).
REVIEW_REQUESTS = (
    (
        "resume_not_match",
        "resume",
        "I led the payments team's move to Kubernetes in 2024, which isn't clear from my résumé.",
        2,
    ),
    ("did_not_pass", "interview", None, 1),
)


async def seed_review_requests(
    session: AsyncSession, workspace_id: uuid.UUID, now: datetime
) -> None:
    """Open review requests on the Senior Backend Engineer pipeline: the oldest application in
    each stage, with its review link already used."""
    pipeline_id = await session.scalar(
        select(Pipeline.id).where(
            Pipeline.workspace_id == workspace_id, Pipeline.title == "Senior Backend Engineer"
        )
    )
    for stage, decision_type, message, days_ago in REVIEW_REQUESTS:
        application = await session.scalar(
            select(Application)
            .where(Application.pipeline_id == pipeline_id, Application.stage == stage)
            .order_by(Application.applied_at)
            .limit(1)
        )
        if application is None:
            continue
        asked = now - timedelta(days=days_ago)
        link = ReviewLink(
            workspace_id=workspace_id,
            application_id=application.id,
            decision_type=decision_type,
            token_hash=new_token_hash()[1],
            expires_at=asked + timedelta(days=25),
            requested_at=asked,
            created_at=asked - timedelta(days=5),
        )
        session.add(link)
        await session.flush()
        session.add(
            HumanReviewRequest(
                workspace_id=workspace_id,
                application_id=application.id,
                decision_type=decision_type,
                review_link_id=link.id,
                candidate_message=message,
                created_at=asked,
            )
        )
        application.review_requested = True
    await session.commit()


# The canvas EditEmailTemplate frame's second wording, saved by Maria.
EDITED_INVITATION = (
    "<p>Hi [Candidate.firstname],</p>"
    "<p>Thank you for applying for [Job.title] at [Company.name]. Your résumé stood out and "
    "we'd like to get to know you better.</p>"
    "<p>Your next step is a short AI interview you can complete in your own time.</p>"
    "<p>Start here: [Interview.link]</p>"
    "<p>The link is open until [Interview.expiry].</p>"
    "<p>Best of luck,<br>The [Company.name] hiring team</p>"
)


async def seed_email_templates(session: AsyncSession, workspace_id: uuid.UUID) -> None:
    await email_templates.ensure_defaults(session, workspace_id)
    maria = next(user for user in USERS if user.key == "maria")
    await email_templates.save(
        session,
        workspace_id,
        maria.id,
        TemplateKey.INTERVIEW_INVITATION,
        subject="You're invited to interview with [Company.name]",
        body_html=EDITED_INVITATION,
    )
    await session.commit()


async def seed_credits(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    departments: dict[str, uuid.UUID],
    members: dict[str, uuid.UUID],
    created: datetime,
    now: datetime,
) -> None:
    """Replays the workspace's history through the credit service: the trial (long expired), a
    credit pack, every pipeline's reserve and applicants, then this month's plan and the
    applicants it paid for, so the plan has 110 left and the pack 1,530 (frame CreditUsage).
    Each used credit is a sample application (DASH-003); this month's are the newest ones."""
    maker = ApplicantMaker(workspace_id, NAMESPACE, EMAIL_DOMAIN)
    zone = ZoneInfo("Asia/Manila")
    await credits.grant_trial(session, workspace_id, granted_at=created)
    from_pack = sum(p.used - p.used_this_month for p in PIPELINES)
    await credits.grant_extra(
        session, workspace_id, credits=EXTRA_LEFT + from_pack, now=now - timedelta(days=60)
    )
    await session.commit()

    pipelines: dict[str, Pipeline] = {}
    applicants: dict[str, list[SampleApplication]] = {}
    for index, sample in enumerate(PIPELINES):
        owner = members[PIPELINE_OWNERS.get(sample.department or "", USERS[0].key)]
        pipeline = Pipeline(
            workspace_id=workspace_id,
            department_id=departments[sample.department] if sample.department else None,
            status="live" if sample.used else sample.status,
            owner_id=owner,
            published_by=None if sample.status == "draft" else owner,
            **pipeline_setup(sample, index, now),
        )
        session.add(pipeline)
        await session.flush()
        pipelines[sample.title] = pipeline
        until = ended_at(sample, pipeline, now) if sample.status in {"closed", "cancelled"} else now
        applicants[sample.title] = maker.plan(pipeline, sample.used, until)

    for sample in PIPELINES:
        pipeline = pipelines[sample.title]
        if sample.reserve:
            await credits.reserve(session, workspace_id, pipeline.id, credits=sample.reserve)
        earlier = applicants[sample.title][: sample.used - sample.used_this_month]
        await maker.add(session, pipeline, earlier, now=now, zone=zone)
        if sample.status in {"closed", "cancelled"}:
            await credits.release(session, workspace_id, pipeline.id)
        await session.commit()

    await credits.grant_plan(
        session,
        workspace_id,
        credits=PLAN_CREDITS,
        period_end=now + timedelta(days=10),
        now=now - timedelta(days=20),
    )
    for sample in PIPELINES:
        latest = applicants[sample.title][sample.used - sample.used_this_month :]
        await maker.add(session, pipelines[sample.title], latest, now=now, zone=zone)
    for sample in PIPELINES:
        pipelines[sample.title].status = sample.status
        if sample.status == "closed":
            closed_on_schedule = sample.title in CLOSED_ON_SCHEDULE
            pipelines[sample.title].closed_reason = "schedule" if closed_on_schedule else "manual"
        if sample.status in {"closed", "cancelled"}:
            pipelines[sample.title].ended_at = ended_at(sample, pipelines[sample.title], now)
    await session.commit()


async def main() -> None:
    url, local = owner_database_url()
    password = os.environ.get("SEED_USER_PASSWORD") or (LOCAL_PASSWORD if local else None)
    if password is None:
        sys.exit("Set SEED_USER_PASSWORD to seed a database that isn't local.")
    engine = create_async_engine(url)
    try:
        seeded = await seed(async_sessionmaker(engine, expire_on_commit=False), password)
    finally:
        await engine.dispose()
    if not seeded:
        print("Acme Talent is already seeded; nothing to do.")
        return
    print(f"Seeded Acme Talent. Sign in as {USERS[0].email} (Admin, owner),")
    print(f"{USERS[1].email} (Recruiter) or {USERS[2].email} (Hiring manager).")
    if password == LOCAL_PASSWORD:
        print(f"Local password for every sample user: {LOCAL_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
