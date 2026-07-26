from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    github_pat: str = Field(alias="GITHUB_PAT")
    anthropic_api_key: str = Field(alias="ANTHROPIC_API_KEY")
    upstash_url: str = Field(alias="UPSTASH_URL")
    upstash_token: str = Field(alias="UPSTASH_TOKEN")
    neon_database_url: str = Field(alias="NEON_DATABASE_URL")
    admin_username: str = Field(alias="ADMIN_USERNAME")
    admin_password: str = Field(alias="ADMIN_PASSWORD")
    allowed_origins: str = Field(alias="ALLOWED_ORIGINS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator(
        "github_pat",
        "anthropic_api_key",
        "upstash_url",
        "upstash_token",
        "neon_database_url",
        "admin_username",
        "admin_password",
    )
    @classmethod
    def require_non_empty_secret(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("required setting must not be empty")
        return value

    @field_validator("allowed_origins")
    @classmethod
    def require_allowed_origins(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("ALLOWED_ORIGINS must include at least one origin")
        return value

    @property
    def allowed_origin_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
