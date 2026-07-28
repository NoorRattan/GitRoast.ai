import asyncio
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.models import Base
from app.dependencies import (
    cache_client_dependency,
    db_session_dependency,
    github_client_dependency,
    rate_limiters_dependency,
)
from app.services.project_evaluator import evaluate_project
from app.services.rate_limit import InMemoryFixedWindowLimiter, RateLimiterRegistry


class MemoryRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value
        return True


class StubRepoClient:
    def __init__(self, bundle):
        self.bundle = bundle
        self.calls = 0

    async def query_repository_evidence(self, repo_url):
        self.calls += 1
        return self.bundle


@pytest.fixture
def repo_bundle():
    files = [
        {
            "path": "README.md",
            "size": 550,
            "truncated": False,
            "text": (
                "Install with npm install. Run with npm run dev. Configure GITHUB_PAT in .env. "
                "Usage example: submit a repo and problem statement. Troubleshooting: retry GitHub rate limits."
            ),
        },
        {
            "path": "package.json",
            "size": 260,
            "truncated": False,
            "text": '{"scripts":{"test":"vitest run","lint":"eslint ."},"dependencies":{"zod":"^3.25.0"}}',
        },
        {
            "path": "src/evaluator.ts",
            "size": 900,
            "truncated": False,
            "text": (
                "import { z } from 'zod'; export async function evaluateRepository(repo, problemStatement) { "
                "const parsed = z.string().parse(problemStatement); const cacheKey = repo + parsed; "
                "await retryWithBackoff(async () => fetch(repo)); return { evidence: [], score: 72, cacheKey }; }"
            ),
        },
        {
            "path": "src/github.ts",
            "size": 500,
            "truncated": False,
            "text": "export async function readTree(cursor) { return fetch(`/tree?first=20&after=${cursor}`); }",
        },
        {
            "path": "tests/evaluator.test.ts",
            "size": 300,
            "truncated": False,
            "text": "it('scores with evidence', () => expect(true).toBe(true));",
        },
        {
            "path": ".github/workflows/ci.yml",
            "size": 220,
            "truncated": False,
            "text": "name: ci\non: [push]\njobs:\n  test:\n    steps:\n      - run: npm test",
        },
    ]
    return {
        "repo_url": "https://github.com/example/evaluator",
        "owner": "example",
        "name": "evaluator",
        "default_branch": "main",
        "commit_sha": "abc123",
        "tree_files": [{"path": file["path"], "type": "blob", "size": file["size"]} for file in files],
        "files": files,
    }


@pytest.fixture
def project_route_harness(required_env, repo_bundle):
    get_settings.cache_clear()
    from app.main import create_app

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def setup_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(setup_db())

    redis = MemoryRedis()
    github = StubRepoClient(repo_bundle)
    limiters = RateLimiterRegistry(
        {
            "post_audit": InMemoryFixedWindowLimiter(100, 3600),
            "opt_out": InMemoryFixedWindowLimiter(100, 3600),
            "get_audit": InMemoryFixedWindowLimiter(100, 3600),
            "card_data": InMemoryFixedWindowLimiter(100, 3600),
            "project_evaluation": InMemoryFixedWindowLimiter(100, 3600),
        }
    )
    app = create_app()

    async def db_override() -> AsyncIterator:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[db_session_dependency] = db_override
    app.dependency_overrides[cache_client_dependency] = lambda: redis
    app.dependency_overrides[github_client_dependency] = lambda: github
    app.dependency_overrides[rate_limiters_dependency] = lambda: limiters

    with TestClient(app) as client:
        yield {"client": client, "redis": redis, "github": github}

    asyncio.run(engine.dispose())


def test_evaluate_project_excludes_accessibility_for_non_ui_repo(repo_bundle):
    repo_bundle["tree_files"] = [
        {"path": "README.md", "type": "blob", "size": 300},
        {"path": "pyproject.toml", "type": "blob", "size": 300},
        {"path": "cli/main.py", "type": "blob", "size": 600},
    ]
    repo_bundle["files"] = [
        {
            "path": "README.md",
            "size": 300,
            "truncated": False,
            "text": "Install with pip install. Usage: python -m cli.",
        },
        {
            "path": "pyproject.toml",
            "size": 300,
            "truncated": False,
            "text": "[project.scripts]\neval='cli.main:main'",
        },
        {
            "path": "cli/main.py",
            "size": 600,
            "truncated": False,
            "text": "def main(): print('evaluate repository problem statement evidence score')",
        },
    ]

    result = evaluate_project(
        "Evaluate a repository against a problem statement with evidence-grounded scoring.",
        repo_bundle,
    )

    assert result.project_type == "cli_tool"
    assert result.excluded_categories == ["accessibility"]
    assert "documentation_accessibility" in result.categories


def test_project_evaluation_route_returns_strict_cached_schema(project_route_harness):
    h = project_route_harness
    payload = {
        "repo_url": "https://github.com/example/evaluator",
        "problem_statement": "Evaluate repositories against a problem statement with strict evidence-based scoring.",
    }

    first = h["client"].post("/api/v1/project-evaluation", json=payload)
    second = h["client"].post("/api/v1/project-evaluation", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert "cached_at" not in second.json()
    assert set(first.json()) == {
        "project_type",
        "excluded_categories",
        "categories",
        "overall_score",
        "grade_label",
        "calibration_note",
        "flags",
    }
    assert len(h["redis"].store) == 1
    assert h["github"].calls == 2


def test_project_evaluation_rejects_non_github_url(project_route_harness):
    response = project_route_harness["client"].post(
        "/api/v1/project-evaluation",
        json={
            "repo_url": "https://gitlab.com/example/evaluator",
            "problem_statement": "Evaluate repositories against a problem statement with strict evidence-based scoring.",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
