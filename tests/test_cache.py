import pytest

from app.services.cache import (
    get_audit_roast,
    get_audit_scores,
    set_audit_roast,
    set_audit_scores,
    should_refresh_stale_entry,
)
from app.services.scoring_constants import CACHE_TTL_SECONDS, SCHEMA_VERSION


class MemoryRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value
        return True


class FailingRedis:
    async def get(self, key):
        raise RuntimeError("redis unavailable")


async def test_audit_scores_round_trip():
    redis = MemoryRedis()
    payload = {
        "scores": {"profile_strength": 80},
        "flags": {"beginner_account": False},
        "findings": [],
        "avatar_url": "https://example.com/avatar.png",
    }

    assert await set_audit_scores(redis, "Noor", SCHEMA_VERSION, payload) is True
    cached = await get_audit_scores(redis, "noor", SCHEMA_VERSION)

    assert cached["scores"] == payload["scores"]
    assert cached["flags"] == payload["flags"]
    assert "cached_at" in cached


async def test_audit_roast_intensities_are_independent():
    redis = MemoryRedis()

    await set_audit_roast(redis, "Noor", "mild", SCHEMA_VERSION, {"roast_text": "mild"})
    await set_audit_roast(redis, "Noor", "hell", SCHEMA_VERSION, {"roast_text": "hell"})

    mild = await get_audit_roast(redis, "Noor", "mild", SCHEMA_VERSION)
    hell = await get_audit_roast(redis, "Noor", "hell", SCHEMA_VERSION)

    assert mild["roast_text"] == "mild"
    assert hell["roast_text"] == "hell"


async def test_cache_get_fails_open(caplog):
    cached = await get_audit_scores(FailingRedis(), "noor", SCHEMA_VERSION)

    assert cached is None
    assert "cache read failed" in caplog.text


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (CACHE_TTL_SECONDS - 60, True),
        (60, False),
        (CACHE_TTL_SECONDS + 1, False),
    ],
)
def test_staleness_helper(age, expected):
    assert should_refresh_stale_entry(age) is expected
