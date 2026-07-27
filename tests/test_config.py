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
