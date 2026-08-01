import asyncio
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request
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
from app.services.github_client import select_evaluation_paths
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

    async def query_repository_revision(self, repo_url):
        self.calls += 1
        return {
            key: self.bundle[key]
            for key in ("repo_url", "owner", "name", "default_branch", "commit_sha")
        }

    async def query_repository_evidence_for_revision(self, revision):
        self.calls += 1
        assert revision["commit_sha"] == self.bundle["commit_sha"]
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
            "admin_auth": InMemoryFixedWindowLimiter(100, 3600),
            "github_capacity": InMemoryFixedWindowLimiter(100, 3600),
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

    with TestClient(app, headers={"x-gitroast-gateway-secret": "test-gateway-secret", "x-gitroast-client-ip": "203.0.113.10"}) as client:
        yield {"client": client, "redis": redis, "github": github, "limiters": limiters}

    asyncio.run(engine.dispose())


def test_evaluate_project_excludes_combined_docs_accessibility_category_for_non_ui_repo(repo_bundle):
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
    assert result.excluded_categories == ["documentation_accessibility"]
    assert "documentation_accessibility" not in result.categories


def test_known_vulnerable_dependency_reduces_security_score(repo_bundle):
    clean = evaluate_project(
        "Evaluate repositories against a problem statement with evidence-grounded scoring.",
        repo_bundle,
    )
    repo_bundle["tree_files"].append({"path": "package.json", "type": "blob", "size": 80})
    repo_bundle["files"].append(
        {
            "path": "package.json",
            "size": 80,
            "truncated": False,
            "text": '{"dependencies":{"axios":"^0.21.0"}}',
        }
    )

    vulnerable = evaluate_project(
        "Evaluate repositories against a problem statement with evidence-grounded scoring.",
        repo_bundle,
    )

    assert vulnerable.categories["security"].score < clean.categories["security"].score
    assert "known-vulnerable dependency" in vulnerable.categories["security"].band_justification


def test_mock_markers_in_test_files_do_not_trigger_stub_cap(repo_bundle):
    repo_bundle["tree_files"] = [
        {"path": "src/service.py", "type": "blob", "size": 400},
        {"path": "tests/test_service.py", "type": "blob", "size": 400},
    ]
    repo_bundle["files"] = [
        {"path": "src/service.py", "size": 400, "truncated": False, "text": "def evaluate(): return 'evidence'"},
        {"path": "tests/test_service.py", "size": 400, "truncated": False, "text": "from unittest.mock import Mock\ndef test_service(): assert Mock()"},
    ]

    result = evaluate_project("Evaluate repository evidence.", repo_bundle)

    assert result.flags.possible_stub_implementation is False


def test_evaluation_path_selection_samples_workspace_packages():
    entries = [
        {"path": "README.md", "size": 100},
        {"path": "package.json", "size": 100},
        {"path": "packages/api/src/index.ts", "size": 100},
        {"path": "packages/web/src/index.ts", "size": 100},
        {"path": "services/worker/main.py", "size": 100},
        {"path": "tools/release.py", "size": 100},
    ]

    selected = select_evaluation_paths(entries, limit=6)

    assert "README.md" in selected
    assert "package.json" in selected
    assert "packages/api/src/index.ts" in selected
    assert "packages/web/src/index.ts" in selected
    assert "services/worker/main.py" in selected


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
    assert h["github"].calls == 3


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


def test_project_evaluation_returns_retry_metadata_when_shared_capacity_is_exhausted(project_route_harness):
    h = project_route_harness
    h["limiters"]._limiters["github_capacity"] = InMemoryFixedWindowLimiter(0, 3600)

    response = h["client"].post(
        "/api/v1/project-evaluation",
        json={
            "repo_url": "https://github.com/example/evaluator",
            "problem_statement": "Evaluate repositories against a problem statement with strict evidence-based scoring.",
        },
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "capacity_limited"
    assert response.headers["Retry-After"]


@pytest.mark.asyncio
async def test_concurrent_matching_evaluations_collect_evidence_once(monkeypatch, repo_bundle):
    from app.models.api import ProjectEvaluationRequest
    from app.routers import project_evaluation as route

    stored = {}

    async def get_cached(*_args):
        return stored.get("value")

    async def set_cached(*_args):
        stored["value"] = _args[-1]

    class RateLimiters:
        async def check(self, *_args):
            return None

        async def check_global(self, *_args):
            return None

    class GitHub:
        revision_calls = 0
        evidence_calls = 0

        async def query_repository_revision(self, _repo_url):
            self.revision_calls += 1
            return {key: repo_bundle[key] for key in ("repo_url", "owner", "name", "default_branch", "commit_sha")}

        async def query_repository_evidence_for_revision(self, _revision):
            self.evidence_calls += 1
            await asyncio.sleep(0.01)
            return repo_bundle

    monkeypatch.setattr(route.cache, "get_project_evaluation", get_cached)
    monkeypatch.setattr(route.cache, "set_project_evaluation", set_cached)
    route._evaluation_locks.clear()
    request = {"type": "http", "method": "POST", "path": "/api/v1/project-evaluation", "headers": [], "client": ("127.0.0.1", 1), "server": ("test", 80), "scheme": "http", "query_string": b"", "root_path": "", "http_version": "1.1"}
    payload = ProjectEvaluationRequest(
        repo_url="https://github.com/example/evaluator",
        problem_statement="Evaluate repositories against a problem statement with strict evidence-based scoring.",
    )
    github = GitHub()

    first, second = await asyncio.gather(
        route.post_project_evaluation(payload, Request(request), object(), github, RateLimiters()),
        route.post_project_evaluation(payload, Request(request), object(), github, RateLimiters()),
    )

    assert first == second
    assert github.revision_calls == 2
    assert github.evidence_calls == 1
