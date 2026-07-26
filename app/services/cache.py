import inspect
import json
import logging
import time
from typing import Any

from app.services.scoring_constants import CACHE_TTL_SECONDS, STALE_REFRESH_WINDOW_SECONDS

logger = logging.getLogger(__name__)


def audit_scores_key(username: str, schema_version: int) -> str:
    return f"audit_scores:{username.lower()}:{schema_version}"


def audit_roast_key(username: str, intensity_applied: str, schema_version: int) -> str:
    return f"audit_roast:{username.lower()}:{intensity_applied.lower()}:{schema_version}"


def should_refresh_stale_entry(age_seconds: int, ttl_seconds: int = CACHE_TTL_SECONDS) -> bool:
    return ttl_seconds - age_seconds <= STALE_REFRESH_WINDOW_SECONDS and age_seconds < ttl_seconds


async def get_audit_scores(client: Any, username: str, schema_version: int) -> dict[str, Any] | None:
    return await _get_json(client, audit_scores_key(username, schema_version))


async def set_audit_scores(client: Any, username: str, schema_version: int, value: dict[str, Any]) -> bool:
    return await _set_json(client, audit_scores_key(username, schema_version), value)


async def get_audit_roast(
    client: Any,
    username: str,
    intensity_applied: str,
    schema_version: int,
) -> dict[str, Any] | None:
    return await _get_json(client, audit_roast_key(username, intensity_applied, schema_version))


async def set_audit_roast(
    client: Any,
    username: str,
    intensity_applied: str,
    schema_version: int,
    value: dict[str, Any],
) -> bool:
    return await _set_json(client, audit_roast_key(username, intensity_applied, schema_version), value)


async def purge_audit_cache(client: Any, username: str, schema_version: int) -> bool:
    keys = [audit_scores_key(username, schema_version)]
    keys.extend(
        audit_roast_key(username, intensity, schema_version)
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
