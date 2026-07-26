import asyncio
import json
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.models import Audit, Base, OptedOutUsername, ReviewQueueItem
from app.dependencies import (
    cache_client_dependency,
    db_session_dependency,
    github_client_dependency,
    rate_limiters_dependency,
)
from app.services.cache import get_audit_roast, set_audit_roast, set_audit_scores
from app.services.github_client import parse_profile_response
from app.services.rate_limit import InMemoryFixedWindowLimiter, RateLimiterRegistry
from app.services.scoring import score_profile
from app.services.scoring_constants import CACHE_TTL_SECONDS, SCHEMA_VERSION


class MemoryRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value
        return True

    async def delete(self, key):
        self.store.pop(key, None)
        return 1


class FailingRedis(MemoryRedis):
    async def get(self, key):
        raise RuntimeError("upstash unavailable")

    async def set(self, key, value, ex=None):
        raise RuntimeError("upstash unavailable")


class StubGitHubClient:
    def __init__(self, profile):
        self.profile = profile
        self.calls = 0

    async def query_user_profile(self, username):
        self.calls += 1
        return self.profile


def roast_payload(text="cached roast"):
    return {
        "roast_text": text,
        "strengths": ["Strong repo", "Readable stack", "Recent work"],
        "improvement_areas": ["Add tests", "Curate pins", "Improve READMEs"],
        "roadmap": [{"week": 1, "focus": "Proof", "actions": ["Add CI"]}],
    }


@pytest.fixture
def route_harness(required_env, load_github_fixture):
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
    github = StubGitHubClient(parse_profile_response(load_github_fixture("small_profile.json")))
    limiters = RateLimiterRegistry(
        {
            "post_audit": InMemoryFixedWindowLimiter(100, 3600),
            "opt_out": InMemoryFixedWindowLimiter(100, 3600),
            "get_audit": InMemoryFixedWindowLimiter(100, 3600),
            "card_data": InMemoryFixedWindowLimiter(100, 3600),
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
        client.app.state.session_factory = session_factory
        client.app.state.github_client = github
        client.app.state.cache_client = redis
        yield {
            "client": client,
            "redis": redis,
            "github": github,
            "session_factory": session_factory,
            "limiters": limiters,
            "app": client.app,
            "engine": engine,
        }

    asyncio.run(engine.dispose())


def run(coro):
    return asyncio.run(coro)


def score_fixture(load_github_fixture, fixture_name):
    return score_profile(parse_profile_response(load_github_fixture(fixture_name)))


def test_audit_scores_cache_hit_skips_github(route_harness, load_github_fixture):
    h = route_harness
    run(set_audit_scores(h["redis"], "cleanbuilder", SCHEMA_VERSION, score_fixture(load_github_fixture, "small_profile.json")))

    response = h["client"].post("/api/v1/audit", json={"username": "cleanbuilder", "roast_intensity": "mild"})

    assert response.status_code == 200
    assert h["github"].calls == 0
    assert response.json()["roast_text"]


def test_roast_cache_hit_skips_regeneration_and_github(route_harness, load_github_fixture, monkeypatch):
    h = route_harness
    scores = score_fixture(load_github_fixture, "small_profile.json")
    run(set_audit_scores(h["redis"], "cleanbuilder", SCHEMA_VERSION, scores))
    run(set_audit_roast(h["redis"], "cleanbuilder", "mild", SCHEMA_VERSION, roast_payload("cached mild")))
    calls = {"count": 0}

    def fail_if_called(*args, **kwargs):
        calls["count"] += 1
        raise AssertionError("roast engine should not run on audit_roast cache hit")

    monkeypatch.setattr("app.routers.audit.generate_roast", fail_if_called)

    response = h["client"].post("/api/v1/audit", json={"username": "cleanbuilder", "roast_intensity": "mild"})

    assert response.status_code == 200
    assert response.json()["roast_text"] == "cached mild"
    assert h["github"].calls == 0
    assert calls["count"] == 0


def test_scores_hit_with_different_roast_intensity_generates_not_github(route_harness, load_github_fixture, monkeypatch):
    h = route_harness
    scores = score_fixture(load_github_fixture, "small_profile.json")
    run(set_audit_scores(h["redis"], "cleanbuilder", SCHEMA_VERSION, scores))
    run(set_audit_roast(h["redis"], "cleanbuilder", "mild", SCHEMA_VERSION, roast_payload("cached mild")))
    calls = {"count": 0}

    def spy_generate_roast(*args, **kwargs):
        calls["count"] += 1
        return roast_payload("fresh hell")

    monkeypatch.setattr("app.routers.audit.generate_roast", spy_generate_roast)

    response = h["client"].post("/api/v1/audit", json={"username": "cleanbuilder", "roast_intensity": "hell"})

    assert response.status_code == 200
    assert response.json()["roast_intensity_applied"] == "hell"
    assert h["github"].calls == 0
    assert calls["count"] == 1


def test_beginner_downgrade_uses_medium_cache_and_skips_github(route_harness, load_github_fixture):
    h = route_harness
    beginner_scores = score_fixture(load_github_fixture, "beginner_account.json")
    run(set_audit_scores(h["redis"], "newstarter", SCHEMA_VERSION, beginner_scores))
    run(set_audit_roast(h["redis"], "newstarter", "medium", SCHEMA_VERSION, roast_payload("cached medium")))

    response = h["client"].post("/api/v1/audit", json={"username": "newstarter", "roast_intensity": "hell"})

    assert response.status_code == 200
    body = response.json()
    assert body["roast_intensity_requested"] == "hell"
    assert body["roast_intensity_applied"] == "medium"
    assert body["intensity_downgraded"] is True
    assert h["github"].calls == 0


def test_stale_scores_hit_schedules_one_refresh(route_harness, load_github_fixture):
    h = route_harness
    scores = score_fixture(load_github_fixture, "small_profile.json")
    scores["cached_at"] = int(__import__("time").time()) - (CACHE_TTL_SECONDS - 60)
    run(set_audit_scores(h["redis"], "cleanbuilder", SCHEMA_VERSION, scores))
    run(set_audit_roast(h["redis"], "cleanbuilder", "mild", SCHEMA_VERSION, roast_payload("cached mild")))

    response = h["client"].post("/api/v1/audit", json={"username": "cleanbuilder", "roast_intensity": "mild"})

    assert response.status_code == 200
    assert h["app"].state.refresh_scheduled_count == 1


def test_cache_down_fails_open_to_github_and_local_generation(route_harness):
    h = route_harness
    h["app"].dependency_overrides[cache_client_dependency] = lambda: FailingRedis()

    response = h["client"].post("/api/v1/audit", json={"username": "cleanbuilder", "roast_intensity": "mild"})

    assert response.status_code == 200
    assert h["github"].calls == 1


def test_opt_out_blocks_post_before_github_or_generation(route_harness, monkeypatch):
    h = route_harness
    calls = {"count": 0}

    def spy_generate_roast(*args, **kwargs):
        calls["count"] += 1
        return roast_payload()

    monkeypatch.setattr("app.routers.audit.generate_roast", spy_generate_roast)

    async def seed():
        async with h["session_factory"]() as db:
            db.add(OptedOutUsername(username="cleanbuilder"))
            await db.commit()

    run(seed())
    response = h["client"].post("/api/v1/audit", json={"username": "cleanbuilder", "roast_intensity": "mild"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "opted_out"
    assert h["github"].calls == 0
    assert calls["count"] == 0


def test_thin_finding_generation_writes_one_review_queue_row_and_cache_hit_writes_zero(route_harness, load_github_fixture):
    h = route_harness
    thin_scores = score_fixture(load_github_fixture, "small_profile.json")
    thin_scores["findings"] = thin_scores["findings"][:2]
    run(set_audit_scores(h["redis"], "thinuser", SCHEMA_VERSION, thin_scores))

    first = h["client"].post("/api/v1/audit", json={"username": "thinuser", "roast_intensity": "mild"})
    second = h["client"].post("/api/v1/audit", json={"username": "thinuser", "roast_intensity": "mild"})

    async def count_reviews():
        async with h["session_factory"]() as db:
            return await db.scalar(select(func.count()).select_from(ReviewQueueItem))

    assert first.status_code == 200
    assert second.status_code == 200
    assert run(count_reviews()) == 1


def test_full_finding_generation_does_not_queue_review_by_default(route_harness):
    h = route_harness
    response = h["client"].post("/api/v1/audit", json={"username": "cleanbuilder", "roast_intensity": "mild"})

    async def count_reviews():
        async with h["session_factory"]() as db:
            return await db.scalar(select(func.count()).select_from(ReviewQueueItem))

    assert response.status_code == 200
    assert run(count_reviews()) == 0


def test_get_audit_blends_never_audited_and_opted_out_404(route_harness):
    h = route_harness
    never = h["client"].get("/api/v1/audit/missing")

    async def seed():
        async with h["session_factory"]() as db:
            db.add(OptedOutUsername(username="privateuser"))
            await db.commit()

    run(seed())
    opted = h["client"].get("/api/v1/audit/privateuser")

    assert never.status_code == 404
    assert opted.status_code == 404
    assert never.json() == opted.json()


def test_card_data_reads_scores_only(route_harness, load_github_fixture):
    h = route_harness
    scores = score_fixture(load_github_fixture, "small_profile.json")
    run(set_audit_scores(h["redis"], "cleanbuilder", SCHEMA_VERSION, scores))

    response = h["client"].get("/api/v1/card-data/cleanbuilder")

    assert response.status_code == 200
    assert response.json() == {
        "username": "cleanbuilder",
        "schema_version": SCHEMA_VERSION,
        "percentile_benchmark": scores["scores"]["percentile_benchmark"],
        "scores": scores["scores"],
        "avatar_url": scores["avatar_url"],
    }


def test_opt_out_purges_cache_and_get_audit_returns_404(route_harness, load_github_fixture):
    h = route_harness
    scores = score_fixture(load_github_fixture, "small_profile.json")
    run(set_audit_scores(h["redis"], "cleanbuilder", SCHEMA_VERSION, scores))
    run(set_audit_roast(h["redis"], "cleanbuilder", "mild", SCHEMA_VERSION, roast_payload("cached mild")))

    response = h["client"].post("/api/v1/opt-out", json={"username": "cleanbuilder"})
    after = h["client"].get("/api/v1/audit/cleanbuilder")

    assert response.status_code == 200
    assert after.status_code == 404
    assert run(get_audit_roast(h["redis"], "cleanbuilder", "mild", SCHEMA_VERSION)) is None


def test_admin_requires_basic_auth_before_listing_reviews(route_harness):
    h = route_harness
    missing = h["client"].get("/api/v1/admin/reviews")
    wrong = h["client"].get("/api/v1/admin/reviews", auth=("admin", "wrong"))
    right = h["client"].get("/api/v1/admin/reviews", auth=("admin", "password"))

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert missing.json()["error"]["code"] == "unauthorized"
    assert right.status_code == 200


def test_admin_can_approve_and_reject_reviews(route_harness):
    h = route_harness

    async def seed():
        async with h["session_factory"]() as db:
            audit = Audit(
                username="cleanbuilder",
                profile_strength=80,
                project_depth=80,
                commit_consistency=80,
                tech_diversity=80,
                percentile_benchmark=80,
                schema_version=SCHEMA_VERSION,
            )
            db.add(audit)
            await db.commit()
            await db.refresh(audit)
            item = ReviewQueueItem(audit_id=audit.id, generated_content=json.dumps(roast_payload()))
            db.add(item)
            await db.commit()
            await db.refresh(item)
            return item.id

    review_id = run(seed())
    approved = h["client"].post(f"/api/v1/admin/reviews/{review_id}/approve", auth=("admin", "password"))
    rejected = h["client"].post(
        f"/api/v1/admin/reviews/{review_id}/reject",
        auth=("admin", "password"),
        json={"reason": "too generic"},
    )

    assert approved.status_code == 200
    assert approved.json()["review_status"] == "approved"
    assert rejected.status_code == 200
    assert rejected.json()["review_status"] == "rejected"
    assert rejected.json()["reason"] == "too generic"


@pytest.mark.parametrize(
    ("method", "path", "json_body", "policy"),
    [
        ("post", "/api/v1/audit", {"username": "cleanbuilder", "roast_intensity": "mild"}, "post_audit"),
        ("post", "/api/v1/opt-out", {"username": "rateuser"}, "opt_out"),
        ("delete", "/api/v1/opt-out/rateuser", None, "opt_out"),
        ("get", "/api/v1/audit/rateuser", None, "get_audit"),
        ("get", "/api/v1/card-data/rateuser", None, "card_data"),
    ],
)
def test_public_rate_limiters_block_n_plus_one_and_reset(route_harness, method, path, json_body, policy):
    h = route_harness
    h["limiters"]._limiters[policy] = InMemoryFixedWindowLimiter(2, 3600)
    request = getattr(h["client"], method)

    first = request(path, json=json_body) if json_body is not None else request(path)
    second = request(path, json=json_body) if json_body is not None else request(path)
    third = request(path, json=json_body) if json_body is not None else request(path)

    assert first.status_code != 429
    assert second.status_code != 429
    assert third.status_code == 429
    assert third.json()["error"]["code"] == "rate_limited"

    h["limiters"]._limiters[policy].reset()
    after_reset = request(path, json=json_body) if json_body is not None else request(path)
    assert after_reset.status_code != 429


def test_error_paths_use_shared_envelope(route_harness):
    response = route_harness["client"].post("/api/v1/audit", json={"username": "", "roast_intensity": "mild"})

    assert response.status_code == 422
    assert set(response.json()) == {"error"}
    assert {"code", "message"} <= set(response.json()["error"])
