import inspect
import json
import logging
import hashlib
import time
from typing import Any

from app.services.scoring_constants import CACHE_TTL_SECONDS, STALE_REFRESH_WINDOW_SECONDS

logger = logging.getLogger(__name__)


def audit_scores_key(username: str, schema_version: int, baseline_version: str = "hand-tuned-v1") -> str:
    return f"audit_scores:{username.lower()}:{schema_version}:{baseline_version}"


def audit_roast_key(username: str, intensity_applied: str, schema_version: int, baseline_version: str = "hand-tuned-v1") -> str:
    return f"audit_roast:{username.lower()}:{intensity_applied.lower()}:{schema_version}:{baseline_version}"


def project_evaluation_key(repo_url: str, commit_sha: str, problem_statement: str, schema_version: int) -> str:
    normalized_repo = repo_url.rstrip("/").lower()
    problem_hash = hashlib.sha256(problem_statement.strip().encode("utf-8")).hexdigest()[:16]
    return f"project_eval:{normalized_repo}:{commit_sha}:{problem_hash}:{schema_version}"


def should_refresh_stale_entry(age_seconds: int, ttl_seconds: int = CACHE_TTL_SECONDS) -> bool:
    return ttl_seconds - age_seconds <= STALE_REFRESH_WINDOW_SECONDS and age_seconds < ttl_seconds


async def get_audit_scores(client: Any, username: str, schema_version: int, baseline_version: str = "hand-tuned-v1") -> dict[str, Any] | None:
    entry = await _get_json(client, audit_scores_key(username, schema_version, baseline_version))
    # Schema v5 entries predate baseline versioning. Keep the documented
    # one-version card transition working without mixing current v6 scores.
    if entry is None and schema_version < 6 and baseline_version == "hand-tuned-v1":
        return await _get_json(client, f"audit_scores:{username.lower()}:{schema_version}")
    return entry


async def set_audit_scores(client: Any, username: str, schema_version: int, value: dict[str, Any], baseline_version: str = "hand-tuned-v1") -> bool:
    return await _set_json(client, audit_scores_key(username, schema_version, baseline_version), value)


async def get_audit_roast(
    client: Any,
    username: str,
    intensity_applied: str,
    schema_version: int,
    baseline_version: str = "hand-tuned-v1",
) -> dict[str, Any] | None:
    return await _get_json(client, audit_roast_key(username, intensity_applied, schema_version, baseline_version))


async def set_audit_roast(
    client: Any,
    username: str,
    intensity_applied: str,
    schema_version: int,
    value: dict[str, Any],
    baseline_version: str = "hand-tuned-v1",
) -> bool:
    return await _set_json(client, audit_roast_key(username, intensity_applied, schema_version, baseline_version), value)


async def get_project_evaluation(
    client: Any,
    repo_url: str,
    commit_sha: str,
    problem_statement: str,
    schema_version: int,
) -> dict[str, Any] | None:
    return await _get_json(client, project_evaluation_key(repo_url, commit_sha, problem_statement, schema_version))


async def set_project_evaluation(
    client: Any,
    repo_url: str,
    commit_sha: str,
    problem_statement: str,
    schema_version: int,
    value: dict[str, Any],
) -> bool:
    return await _set_json(client, project_evaluation_key(repo_url, commit_sha, problem_statement, schema_version), value)


async def purge_audit_cache(client: Any, username: str, schema_version: int, baseline_versions: tuple[str, ...] = ("hand-tuned-v1",)) -> bool:
    keys = [audit_scores_key(username, schema_version, baseline) for baseline in baseline_versions]
    keys.extend(
        audit_roast_key(username, intensity, schema_version, baseline)
        for baseline in baseline_versions
        for intensity in ("mild", "medium", "brutal", "hell")
    )
    ok = True
    for key in keys:
        try:
            await _maybe_await(client.delete(key))
        except Exception:
            logger.exception("cache delete failed", extra={"cache_key": key})
            ok = False
    return ok


async def _get_json(client: Any, key: str) -> dict[str, Any] | None:
    try:
        raw = await _maybe_await(client.get(key))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)
    except Exception:
        logger.exception("cache read failed", extra={"cache_key": key})
        return None


async def _set_json(client: Any, key: str, value: dict[str, Any]) -> bool:
    payload = json.dumps({"cached_at": int(time.time()), **value}, separators=(",", ":"))
    try:
        if hasattr(client, "set"):
            await _maybe_await(client.set(key, payload, ex=CACHE_TTL_SECONDS))
        else:
            await _maybe_await(client.setex(key, CACHE_TTL_SECONDS, payload))
        return True
    except Exception:
        logger.exception("cache write failed", extra={"cache_key": key})
        return False


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def create_upstash_client(url: str, token: str) -> Any:
    from upstash_redis.asyncio import Redis

    return Redis(url=url, token=token)
