import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError
from app.db.models import Audit, OptedOutUsername, ReviewQueueItem
from app.dependencies import (
    cache_client_dependency,
    db_session_dependency,
    github_client_dependency,
    llm_client_dependency,
    rate_limiters_dependency,
)
from app.models.api import AuditRequest
from app.services import cache
from app.services.github_client import GitHubClientError, GitHubGraphQLClient
from app.services.llm_client import AnthropicRoastClient, LLMClientError, repo_evidence_from_profile
from app.services.rate_limit import RateLimiterRegistry
from app.services.scoring import score_profile
from app.services.scoring_constants import SCHEMA_VERSION

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


@router.post("/audit")
async def post_audit(
    payload: AuditRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(db_session_dependency),
    cache_client=Depends(cache_client_dependency),
    github_client: GitHubGraphQLClient = Depends(github_client_dependency),
    llm_client: AnthropicRoastClient = Depends(llm_client_dependency),
    rate_limiters: RateLimiterRegistry = Depends(rate_limiters_dependency),
) -> dict[str, Any]:
    await rate_limiters.check("post_audit", request)
    username = payload.username
    if await _is_opted_out(db, username):
        raise APIError(409, "opted_out", "This username has opted out of GitRoast.ai audits.")

    scores_entry = await cache.get_audit_scores(cache_client, username, SCHEMA_VERSION)
    profile: dict[str, Any] | None = None
    score_cache_hit = scores_entry is not None
    audit_row: Audit | None = None

    if scores_entry is None:
        try:
            profile = await github_client.query_user_profile(username)
        except GitHubClientError as exc:
            if exc.status_code == 404:
                raise APIError(404, "not_found", "GitHub user not found.") from exc
            raise APIError(503, "github_unavailable", "GitHub is temporarily unavailable.") from exc
        scores_entry = score_profile(profile)
        await cache.set_audit_scores(cache_client, username, SCHEMA_VERSION, scores_entry)
        audit_row = await _insert_audit(db, username, scores_entry["scores"])
    else:
        _schedule_stale_refresh_if_needed(request, background_tasks, username, scores_entry)

    intensity_applied = _apply_beginner_downgrade(payload.roast_intensity, scores_entry["flags"])
    intensity_downgraded = intensity_applied != payload.roast_intensity
    roast_entry = await cache.get_audit_roast(cache_client, username, intensity_applied, SCHEMA_VERSION)

    if roast_entry is None:
        try:
            roast_entry = await llm_client.generate_roast(
                username=username,
                scores=scores_entry["scores"],
                flags=scores_entry["flags"],
                findings=scores_entry["findings"],
                roast_intensity_applied=intensity_applied,
                repo_evidence=repo_evidence_from_profile(profile or {"repos": []}),
            )
        except LLMClientError as exc:
            raise APIError(503, "llm_unavailable", "Roast generation is temporarily unavailable.") from exc
        await cache.set_audit_roast(cache_client, username, intensity_applied, SCHEMA_VERSION, roast_entry)
        if audit_row is None:
            audit_row = await _latest_audit(db, username)
        if audit_row is None:
            audit_row = await _insert_audit(db, username, scores_entry["scores"])
        await _insert_review_queue(db, audit_row.id, roast_entry)

    return _audit_response(
        username=username,
        cache_hit=score_cache_hit and "cached_at" in roast_entry,
        requested=payload.roast_intensity,
        applied=intensity_applied,
        downgraded=intensity_downgraded,
        scores_entry=scores_entry,
        roast_entry=roast_entry,
    )


@router.get("/audit/{username}")
async def get_audit(
    username: str,
    request: Request,
    db: AsyncSession = Depends(db_session_dependency),
    cache_client=Depends(cache_client_dependency),
    rate_limiters: RateLimiterRegistry = Depends(rate_limiters_dependency),
) -> dict[str, Any]:
    await rate_limiters.check("get_audit", request)
    if await _is_opted_out(db, username):
        raise APIError(404, "not_found", "Audit not found.")
    scores_entry = await cache.get_audit_scores(cache_client, username, SCHEMA_VERSION)
    if scores_entry is None:
        raise APIError(404, "not_found", "Audit not found.")

    for intensity in ("medium", "mild", "brutal", "hell"):
        roast_entry = await cache.get_audit_roast(cache_client, username, intensity, SCHEMA_VERSION)
        if roast_entry is not None:
            return _audit_response(
                username=username,
                cache_hit=True,
                requested=intensity,
                applied=intensity,
                downgraded=False,
                scores_entry=scores_entry,
                roast_entry=roast_entry,
            )
    raise APIError(404, "not_found", "Audit not found.")


async def _is_opted_out(db: AsyncSession, username: str) -> bool:
    result = await db.execute(
        select(OptedOutUsername).where(OptedOutUsername.username == username.lower())
    )
    return result.scalar_one_or_none() is not None


async def _insert_audit(db: AsyncSession, username: str, scores: dict[str, int]) -> Audit:
    audit = Audit(
        username=username.lower(),
        profile_strength=scores["profile_strength"],
        project_depth=scores["project_depth"],
        commit_consistency=scores["commit_consistency"],
        tech_diversity=scores["tech_diversity"],
        percentile_benchmark=scores["percentile_benchmark"],
        schema_version=SCHEMA_VERSION,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)
    return audit


async def _latest_audit(db: AsyncSession, username: str) -> Audit | None:
    result = await db.execute(
        select(Audit)
        .where(Audit.username == username.lower(), Audit.schema_version == SCHEMA_VERSION)
        .order_by(desc(Audit.created_at), desc(Audit.id))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _insert_review_queue(db: AsyncSession, audit_id: int, roast_entry: dict[str, Any]) -> None:
    item = ReviewQueueItem(audit_id=audit_id, generated_content=json.dumps(roast_entry, separators=(",", ":")))
    db.add(item)
    await db.commit()


def _apply_beginner_downgrade(requested: str, flags: dict[str, bool]) -> str:
    if flags.get("beginner_account") and requested in {"brutal", "hell"}:
        return "medium"
    return requested


def _audit_response(
    *,
    username: str,
    cache_hit: bool,
    requested: str,
    applied: str,
    downgraded: bool,
    scores_entry: dict[str, Any],
    roast_entry: dict[str, Any],
) -> dict[str, Any]:
    return {
        "username": username,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "cache_hit": cache_hit,
        "roast_intensity_requested": requested,
        "roast_intensity_applied": applied,
        "intensity_downgraded": downgraded,
        "scores": scores_entry["scores"],
        "flags": scores_entry["flags"],
        "findings": scores_entry["findings"],
        "roast_text": roast_entry["roast_text"],
        "strengths": roast_entry["strengths"],
        "improvement_areas": roast_entry["improvement_areas"],
        "roadmap": roast_entry["roadmap"],
    }


def _schedule_stale_refresh_if_needed(
    request: Request,
    background_tasks: BackgroundTasks,
    username: str,
    scores_entry: dict[str, Any],
) -> None:
    cached_at = scores_entry.get("cached_at")
    if cached_at is None:
        return
    age = int(datetime.now(UTC).timestamp()) - int(cached_at)
    if not cache.should_refresh_stale_entry(age):
        return
    key = f"audit_scores:{username.lower()}:{SCHEMA_VERSION}"
    scheduled = request.app.state.refresh_locks
    if key in scheduled:
        return
    scheduled.add(key)
    request.app.state.refresh_scheduled_count += 1
    background_tasks.add_task(_refresh_scores_task, request.app, username, key)


async def _refresh_scores_task(app, username: str, key: str) -> None:
    try:
        async with app.state.session_factory() as db:
            profile = await app.state.github_client.query_user_profile(username)
            scores_entry = score_profile(profile)
            await cache.set_audit_scores(app.state.cache_client, username, SCHEMA_VERSION, scores_entry)
            await _insert_audit(db, username, scores_entry["scores"])
    except Exception:
        logger.exception("stale audit refresh failed", extra={"username": username})
    finally:
        app.state.refresh_locks.discard(key)
