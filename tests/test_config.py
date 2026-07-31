import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_requires_every_secret(required_env, monkeypatch):
    monkeypatch.delenv("GITHUB_PAT")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_parses_allowed_origins(required_env):
    settings = Settings(_env_file=None)

    assert settings.allowed_origin_list == ["http://localhost:3000", "https://gitroast-ai-frontend.jnoorrattan.workers.dev"]
    assert settings.github_capacity_mode == "shadow"


@pytest.mark.parametrize(
    "allowed_origins",
    [
        "*",
        "localhost:3000",
        "https://gitroast-ai-frontend.jnoorrattan.workers.dev/api",
    ],
)
def test_settings_rejects_invalid_allowed_origins(required_env, monkeypatch, allowed_origins):
    monkeypatch.setenv("ALLOWED_ORIGINS", allowed_origins)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
