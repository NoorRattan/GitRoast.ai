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
    rate_limiters_dependency,
)
from app.models.api import AuditRequest
from app.services import cache
from app.services.benchmark import apply_percentile_benchmark, calculate_percentile_benchmark
from app.services.github_client import GitHubClientError, GitHubGraphQLClient
from app.services.rate_limit import RateLimiterRegistry
from app.services.roast_engine import generate_roast, should_queue_for_review
from app.services.scoring import score_profile
from app.services.scoring_constants import SCHEMA_VERSION
from app.services.signal_baselines import baseline_status, config_baselines, latest_signal_baseline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

ROAST_TONE_GUIDANCE = {
    "mild": "Constructive and encouraging.",
    "medium": "Direct, but focused on the work.",
    "brutal": "Sharper criticism of the public signals, never the person.",
    "hell": "Maximum theatrical heat aimed at the public work, never the person.",
}
AUDIT_SCOPE = "Public GitHub signals only; directional, not a code review."
AUDIT_LIMITATIONS = [
    "Only visible profile, repository, README, and sampled commit data are inspected.",
    "Private work, code execution, issue quality, and off-GitHub collaboration are not measured.",
]


@router.post("/audit")
async def post_audit(
    payload: AuditRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(db_session_dependency),
    cache_client=Depends(cache_client_dependency),
    github_client: GitHubGraphQLClient = Depends(github_client_dependency),
    rate_limiters: RateLimiterRegistry = Depends(rate_limiters_dependency),
) -> dict[str, Any]:
    await rate_limiters.check("post_audit", request)
    username = payload.username
    if await _is_opted_out(db, username):
        raise APIError(409, "opted_out", "This username has opted out of GitRoast.ai audits.")

    baseline_config = await latest_signal_baseline(db)
    baseline_version = baseline_config.version if baseline_config else "hand-tuned-v1"
    scores_entry = await cache.get_audit_scores(cache_client, username, SCHEMA_VERSION, baseline_version)
    profile: dict[str, Any] | None = None
    score_cache_hit = scores_entry is not None
    audit_row: Audit | None = None

    if scores_entry is None:
        await rate_limiters.check_global("github_capacity", request)
        try:
            profile = await github_client.query_user_profile(username)
        except GitHubClientError as exc:
            if exc.status_code == 404:
                raise APIError(404, "not_found", "GitHub user not found.") from exc
            raise APIError(503, "github_unavailable", "GitHub is temporarily unavailable.") from exc
        scores_entry = score_profile(profile, healthy_baselines=config_baselines(baseline_config))
        scores_entry["baseline_version"] = baseline_version
        benchmark = await calculate_percentile_benchmark(
            db,
            username=username,
            scores=scores_entry["scores"],
            account_age_months=scores_entry["account_age_months"],
        )
        apply_percentile_benchmark(scores_entry, benchmark)
        await cache.set_audit_scores(cache_client, username, SCHEMA_VERSION, scores_entry, baseline_version)
        audit_row = await _insert_audit(
            db,
            username,
            scores_entry["scores"],
            account_age_months=scores_entry["account_age_months"],
            metric_snapshot=scores_entry.get("metric_snapshot"),
        )
    else:
        _schedule_stale_refresh_if_needed(request, background_tasks, username, scores_entry)

    intensity_applied = _apply_beginner_downgrade(payload.roast_intensity, scores_entry["flags"])
    intensity_downgraded = intensity_applied != payload.roast_intensity
    roast_entry = await cache.get_audit_roast(cache_client, username, intensity_applied, SCHEMA_VERSION, baseline_version)
    roast_cache_hit = roast_entry is not None

    if roast_entry is None:
        roast_entry = generate_roast(
            findings=scores_entry["findings"],
            scores=scores_entry["scores"],
            intensity_applied=intensity_applied,
        )
        await cache.set_audit_roast(cache_client, username, intensity_applied, SCHEMA_VERSION, roast_entry, baseline_version)
        # Review queue now flags thin deterministic assemblies for line-bank editing, not every generation.
        if should_queue_for_review(scores_entry["findings"]):
            if audit_row is None:
                audit_row = await _latest_audit(db, username)
            if audit_row is None:
                audit_row = await _insert_audit(
                    db,
                    username,
                    scores_entry["scores"],
                    account_age_months=scores_entry.get("account_age_months"),
                )
            await _insert_review_queue(db, audit_row.id, roast_entry)

    response = _audit_response(
        username=username,
        cache_hit=score_cache_hit and roast_cache_hit,
        requested=payload.roast_intensity,
        applied=intensity_applied,
        downgraded=intensity_downgraded,
        scores_entry=scores_entry,
        roast_entry=roast_entry,
        distributional_status=await baseline_status(db),
    )
    _log_audit_completed(
        username=username,
        method="POST",
        score_cache_hit=score_cache_hit,
        roast_cache_hit=roast_cache_hit,
        intensity_applied=intensity_applied,
        github_rate_limit_remaining=getattr(github_client, "last_rate_limit_remaining", None),
    )
    return response


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
    baseline_config = await latest_signal_baseline(db)
    baseline_version = baseline_config.version if baseline_config else "hand-tuned-v1"
    scores_entry = await cache.get_audit_scores(cache_client, username, SCHEMA_VERSION, baseline_version)
    if scores_entry is None:
        raise APIError(404, "not_found", "Audit not found.")

    for intensity in ("medium", "mild", "brutal", "hell"):
        roast_entry = await cache.get_audit_roast(cache_client, username, intensity, SCHEMA_VERSION, baseline_version)
        if roast_entry is not None:
            response = _audit_response(
                username=username,
                cache_hit=True,
                requested=intensity,
                applied=intensity,
                downgraded=False,
                scores_entry=scores_entry,
                roast_entry=roast_entry,
                distributional_status=await baseline_status(db),
            )
            _log_audit_completed(
                username=username,
                method="GET",
                score_cache_hit=True,
                roast_cache_hit=True,
                intensity_applied=intensity,
                github_rate_limit_remaining=None,
            )
            return response
    raise APIError(404, "not_found", "Audit not found.")


async def _is_opted_out(db: AsyncSession, username: str) -> bool:
    result = await db.execute(
        select(OptedOutUsername).where(OptedOutUsername.username == username.lower())
    )
    return result.scalar_one_or_none() is not None


async def _insert_audit(
    db: AsyncSession,
    username: str,
    scores: dict[str, int],
    *,
    account_age_months: int | None,
    metric_snapshot: dict[str, Any] | None = None,
) -> Audit:
    audit = Audit(
        username=username.lower(),
        profile_strength=scores["profile_strength"],
        project_depth=scores["project_depth"],
        commit_consistency=scores["commit_consistency"],
        tech_diversity=scores["tech_diversity"],
        percentile_benchmark=scores["percentile_benchmark"],
        account_age_months=account_age_months,
        schema_version=SCHEMA_VERSION,
        metric_snapshot=metric_snapshot,
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
    distributional_status: dict[str, Any],
) -> dict[str, Any]:
    return {
        "username": username,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "schema_version": SCHEMA_VERSION,
        "cache_hit": cache_hit,
        "roast_intensity_requested": requested,
        "roast_intensity_applied": applied,
        "intensity_downgraded": downgraded,
        "scores": scores_entry["scores"],
        "flags": scores_entry["flags"],
        "findings": scores_entry["findings"],
        "percentile_sample_size": scores_entry.get("percentile_sample_size", 0),
        "percentile_cold_start": scores_entry.get("percentile_cold_start", True),
        "distributional_calibration": distributional_status,
        "report_context": {
            "scope": AUDIT_SCOPE,
            "limitations": AUDIT_LIMITATIONS,
            "roast_tone": ROAST_TONE_GUIDANCE[applied],
        },
        "roast_text": roast_entry["roast_text"],
        "strengths": roast_entry["strengths"],
        "improvement_areas": roast_entry["improvement_areas"],
        "roadmap": roast_entry["roadmap"],
    }


def _log_audit_completed(
    *,
    username: str,
    method: str,
    score_cache_hit: bool,
    roast_cache_hit: bool,
    intensity_applied: str,
    github_rate_limit_remaining: int | None,
) -> None:
    logger.info(
        "audit completed",
        extra={
            "username": username,
            "method": method,
            "score_cache_hit": score_cache_hit,
            "roast_cache_hit": roast_cache_hit,
            "roast_intensity_applied": intensity_applied,
            "github_rate_limit_remaining": github_rate_limit_remaining,
        },
    )


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
        await app.state.rate_limiters.check_global("github_capacity")
        async with app.state.session_factory() as db:
            profile = await app.state.github_client.query_user_profile(username)
            scores_entry = score_profile(profile)
            benchmark = await calculate_percentile_benchmark(
                db,
                username=username,
                scores=scores_entry["scores"],
                account_age_months=scores_entry["account_age_months"],
            )
            apply_percentile_benchmark(scores_entry, benchmark)
            await cache.set_audit_scores(app.state.cache_client, username, SCHEMA_VERSION, scores_entry)
            await _insert_audit(
                db,
                username,
                scores_entry["scores"],
                account_age_months=scores_entry["account_age_months"],
                metric_snapshot=scores_entry.get("metric_snapshot"),
            )
    except Exception:
        logger.exception("stale audit refresh failed", extra={"username": username})
    finally:
        app.state.refresh_locks.discard(key)
