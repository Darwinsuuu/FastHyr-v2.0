"""Application settings, read from environment variables (see .env.example)."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    web_origins: Annotated[list[str], NoDecode] = [
        "http://fasthyr.localhost:3000",
        "http://app.fasthyr.localhost:3000",
    ]
    database_url: str = "postgresql://fasthyr_api:fasthyr_api_local@127.0.0.1:54322/postgres"
    supabase_url: str = "http://127.0.0.1:54321"
    supabase_service_role_key: str = ""
    # Empty means "derive from SUPABASE_URL", which is right for every Supabase project.
    supabase_jwks_url: str = ""
    supabase_jwt_issuer: str = ""
    supabase_jwt_audience: str = "authenticated"
    # Redis for the arq job queue (FND-008). Local Redis runs in Docker (`make redis-start`).
    redis_url: str = "redis://127.0.0.1:6379"
    # Links in emails (FND-010) point at the site host.
    site_url: str = "http://fasthyr.localhost:3000"
    # Email (FND-010, ADR-008). `auto` sends through Resend when RESEND_API_KEY is set, else to
    # local Mailpit over SMTP when APP_ENV is local, else only logs the message ID.
    email_backend: Literal["auto", "resend", "smtp", "log"] = "auto"
    email_from_address: str = "no-reply@fasthyr.com"
    resend_api_key: str = ""
    resend_webhook_secret: str = ""
    # Local Supabase's Mailpit (supabase/config.toml [local_smtp] smtp_port).
    smtp_host: str = "127.0.0.1"
    smtp_port: int = 54325

    # OpenAI (FND-013, ADR-007). Model names are configuration, never hard-coded.
    openai_api_key: str = ""
    openai_text_model: str = ""
    openai_timeout_seconds: float = 60
    # USD per million tokens, per model, for ai_calls.cost_usd, as JSON:
    # {"<model>": {"input": 0.0, "output": 0.0}}. A model without a price logs a null cost.
    openai_prices: dict[str, dict[str, float]] = {}
    # AI_FAKE=1 answers every AI call from fixtures (app/ai/fixtures/), with no network.
    ai_fake: bool = False

    # Observability (FND-009). An empty SENTRY_DSN sends nothing. The API and worker are separate
    # Sentry projects, so each Render service sets its own DSN.
    sentry_dsn: str = ""
    # Defaults to APP_ENV.
    sentry_environment: str = ""
    sentry_traces_sample_rate: float = 0.0
    # The release tag is the git SHA; Render sets RENDER_GIT_COMMIT on every deploy.
    git_sha: str = ""
    render_git_commit: str = ""
    log_level: str = "INFO"
    # Empty means console lines locally and JSON everywhere else.
    log_format: Literal["", "json", "console"] = ""

    @field_validator("web_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def resolved_email_backend(self) -> str:
        if self.email_backend != "auto":
            return self.email_backend
        if self.resend_api_key:
            return "resend"
        return "smtp" if self.app_env == "local" else "log"

    @property
    def release(self) -> str | None:
        return self.git_sha or self.render_git_commit or None

    @property
    def resolved_log_format(self) -> Literal["json", "console"]:
        if self.log_format:
            return self.log_format
        return "console" if self.app_env == "local" else "json"

    @property
    def jwks_url(self) -> str:
        return self.supabase_jwks_url or f"{self.auth_url}/.well-known/jwks.json"

    @property
    def jwt_issuer(self) -> str:
        return self.supabase_jwt_issuer or self.auth_url

    @property
    def auth_url(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def async_database_url(self) -> str:
        """`DATABASE_URL` with the asyncpg driver, as SQLAlchemy's async engine needs."""
        scheme, _, rest = self.database_url.partition("://")
        if scheme in ("postgres", "postgresql"):
            return f"postgresql+asyncpg://{rest}"
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
