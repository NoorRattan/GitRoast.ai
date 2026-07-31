from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    github_pat: str = Field(alias="GITHUB_PAT")
    upstash_url: str = Field(alias="UPSTASH_URL")
    upstash_token: str = Field(alias="UPSTASH_TOKEN")
    neon_database_url: str = Field(alias="NEON_DATABASE_URL")
    admin_username: str = Field(alias="ADMIN_USERNAME")
    admin_password: str = Field(alias="ADMIN_PASSWORD")
    gateway_shared_secret: str = Field(alias="GATEWAY_SHARED_SECRET")
    allowed_origins: str = Field(alias="ALLOWED_ORIGINS")
    github_capacity_per_hour: int = Field(default=250, alias="GITHUB_CAPACITY_PER_HOUR", ge=1, le=4_500)
    github_capacity_mode: Literal["shadow", "enforce"] = Field(default="shadow", alias="GITHUB_CAPACITY_MODE")
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator(
        "github_pat",
        "upstash_url",
        "upstash_token",
        "neon_database_url",
        "admin_username",
        "admin_password",
        "gateway_shared_secret",
    )
    @classmethod
    def require_non_empty_secret(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("required setting must not be empty")
        return value

    @field_validator("allowed_origins")
    @classmethod
    def require_allowed_origins(cls, value: str) -> str:
        origins = [item.strip() for item in value.split(",") if item.strip()]
        if not origins:
            raise ValueError("ALLOWED_ORIGINS must include at least one origin")
        for origin in origins:
            parsed = urlparse(origin)
            if origin == "*":
                raise ValueError("ALLOWED_ORIGINS cannot use '*' because credentials are enabled")
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("ALLOWED_ORIGINS entries must be absolute http(s) origins")
            if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
                raise ValueError("ALLOWED_ORIGINS entries must not include paths, queries, or fragments")
        return value

    @property
    def allowed_origin_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
