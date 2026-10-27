"""FastAPI app factory. Routers and middleware are registered here."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.ai.realtime import RealtimeProvider, realtime_from_settings
from app.api.routers import (
    analytics,
    applications,
    candidate,
    candidates,
    company_profile,
    credits,
    departments,
    dev,
    integrity_flags,
    invites,
    jobs,
    me,
    members,
    pipelines,
    public_notices,
    public_pipelines,
    public_review_requests,
    review_requests,
    webhooks_resend,
    workspaces,
)
from app.compliance.notices import released
from app.core.auth import TokenVerifier
from app.core.config import Settings, get_settings
from app.core.db import create_engine, create_sessionmaker
from app.core.errors import register_error_handlers
from app.core.logging import REQUEST_ID_HEADER, RequestIdMiddleware, configure_logging
from app.core.observability import init_sentry
from app.integrations.storage import Storage, storage_from_settings
from app.jobs.queue import JobQueue

API_PREFIX = "/v1"


class HealthResponse(BaseModel):
    status: str


def create_app(
    settings: Settings | None = None,
    token_verifier: TokenVerifier | None = None,
    job_queue: JobQueue | None = None,
    storage: Storage | None = None,
    realtime: RealtimeProvider | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.resolved_log_format)
    init_sentry(settings, "api")
    # A notice edited after release stops the API from starting (COMP-002).
    released()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings)
        app.state.sessionmaker = create_sessionmaker(engine)
        yield
        await app.state.job_queue.close()
        await engine.dispose()

    app = FastAPI(
        title="FastHyr API",
        version="0.1.0",
        lifespan=lifespan,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.token_verifier = token_verifier or TokenVerifier.from_settings(settings)
    app.state.job_queue = job_queue or JobQueue(settings.redis_url)
    app.state.storage = storage or storage_from_settings(settings)
    app.state.realtime = realtime or realtime_from_settings(settings)

    register_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.web_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type", "X-Workspace-Id", "Idempotency-Key"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    # Added last so it runs first: every response, CORS and errors included, carries the ID.
    app.add_middleware(RequestIdMiddleware)

    # Render's health check calls this; it stays outside /v1 and needs no sign-in.
    @app.get("/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    v1 = APIRouter(prefix=API_PREFIX)
    v1.include_router(me.router)
    v1.include_router(workspaces.router)
    v1.include_router(departments.router)
    v1.include_router(company_profile.router)
    v1.include_router(company_profile.public_router)
    v1.include_router(analytics.router)
    v1.include_router(pipelines.router)
    v1.include_router(applications.router)
    v1.include_router(integrity_flags.router)
    v1.include_router(review_requests.router)
    v1.include_router(candidates.router)
    v1.include_router(public_pipelines.router)
    v1.include_router(public_notices.router)
    v1.include_router(public_review_requests.router)
    v1.include_router(candidate.router)
    v1.include_router(credits.router)
    v1.include_router(members.router)
    v1.include_router(invites.router)
    v1.include_router(jobs.router)
    v1.include_router(webhooks_resend.router)
    if settings.app_env in ("local", "development"):
        v1.include_router(dev.router)
    app.include_router(v1)

    return app


app = create_app()
