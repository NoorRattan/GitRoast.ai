import json
from pathlib import Path

import pytest


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "github"


@pytest.fixture
def load_github_fixture():
    def _load(name: str) -> dict:
        return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))

    return _load


@pytest.fixture
def required_env(monkeypatch):
    values = {
        "GITHUB_PAT": "ghp_test",
        "UPSTASH_URL": "https://example.upstash.io",
        "UPSTASH_TOKEN": "upstash_test",
        "NEON_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "password",
        "ALLOWED_ORIGINS": "http://localhost:3000,https://gitroast-ai-frontend.jnoorrattan.workers.dev",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return values
