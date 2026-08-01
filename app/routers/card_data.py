from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError
from app.db.models import OptedOutUsername
from app.dependencies import cache_client_dependency, db_session_dependency, rate_limiters_dependency
from app.services.cache import get_audit_scores
from app.services.rate_limit import RateLimiterRegistry
from app.services.scoring_constants import SCHEMA_VERSION
from app.services.signal_baselines import latest_signal_baseline

router = APIRouter(prefix="/api/v1")
PREVIOUS_SCHEMA_VERSION = SCHEMA_VERSION - 1


@router.get("/card-data/{username}")
async def get_card_data(
    username: str,
    request: Request,
    db: AsyncSession = Depends(db_session_dependency),
    cache_client=Depends(cache_client_dependency),
    rate_limiters: RateLimiterRegistry = Depends(rate_limiters_dependency),
) -> dict:
    await rate_limiters.check("card_data", request)
    result = await db.execute(
        select(OptedOutUsername).where(OptedOutUsername.username == username.lower())
    )
    if result.scalar_one_or_none() is not None:
        raise APIError(404, "not_found", "Audit not found.")
    baseline = await latest_signal_baseline(db)
    baseline_version = baseline.version if baseline else "hand-tuned-v1"
    scores_entry = await get_audit_scores(cache_client, username, SCHEMA_VERSION, baseline_version)
    if scores_entry is None and PREVIOUS_SCHEMA_VERSION > 0:
        scores_entry = await get_audit_scores(cache_client, username, PREVIOUS_SCHEMA_VERSION)
    if scores_entry is None:
        raise APIError(404, "not_found", "Audit not found.")
    return {
        "username": username,
        "schema_version": scores_entry.get("schema_version", SCHEMA_VERSION),
        "percentile_benchmark": scores_entry["scores"]["percentile_benchmark"],
        "percentile_sample_size": scores_entry.get("percentile_sample_size", 0),
        "percentile_cold_start": scores_entry.get("percentile_cold_start", True),
        "scores": scores_entry["scores"],
        "avatar_url": scores_entry.get("avatar_url"),
    }
