"""Application settings, read from environment variables (see .env.example)."""

from functools import lru_cache
from typing import Annotated

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

    @field_validator("web_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

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
