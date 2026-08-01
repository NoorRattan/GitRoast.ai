import json
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError
from app.core.security import require_admin
from app.db.models import ReviewQueueItem, ReviewStatus, SignalBaselineConfiguration
from app.dependencies import db_session_dependency
from app.models.api import ActivateSignalBaselineRequest, RejectReviewRequest, ReviewStatusValue
from app.dependencies import rate_limiters_dependency
from app.services.rate_limit import RateLimiterRegistry
from app.services.signal_baselines import baseline_status, build_signal_baseline


async def limit_admin_auth(
    request: Request,
    rate_limiters: RateLimiterRegistry = Depends(rate_limiters_dependency),
) -> None:
    await rate_limiters.check("admin_auth", request)


router = APIRouter(prefix="/api/v1/admin", dependencies=[Depends(limit_admin_auth), Depends(require_admin)])


@router.get("/reviews")
async def list_reviews(
    status: ReviewStatusValue = "pending",
    db: AsyncSession = Depends(db_session_dependency),
) -> dict[str, list[dict[str, Any]]]:
    result = await db.execute(
        select(ReviewQueueItem)
        .where(ReviewQueueItem.review_status == ReviewStatus(status))
        .order_by(ReviewQueueItem.created_at.asc())
    )
    return {"reviews": [_review_payload(item) for item in result.scalars().all()]}


@router.post("/reviews/{review_id}/approve")
async def approve_review(
    review_id: int,
    db: AsyncSession = Depends(db_session_dependency),
) -> dict[str, str | int]:
    item = await db.get(ReviewQueueItem, review_id)
    if item is None:
        raise APIError(404, "not_found", "Review item not found.")
    item.review_status = ReviewStatus.approved
    item.reason = None
    await db.commit()
    return {"id": item.id, "review_status": item.review_status.value}


@router.post("/reviews/{review_id}/reject")
async def reject_review(
    review_id: int,
    payload: RejectReviewRequest | None = None,
    db: AsyncSession = Depends(db_session_dependency),
) -> dict[str, str | int | None]:
    item = await db.get(ReviewQueueItem, review_id)
    if item is None:
        raise APIError(404, "not_found", "Review item not found.")
    item.review_status = ReviewStatus.rejected
    item.reason = payload.reason if payload else None
    await db.commit()
    return {"id": item.id, "review_status": item.review_status.value, "reason": item.reason}


def _review_payload(item: ReviewQueueItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "audit_id": item.audit_id,
        "generated_content": json.loads(item.generated_content),
        "review_status": item.review_status.value,
        "reason": item.reason,
        "created_at": item.created_at.isoformat(),
    }


@router.get("/signal-baselines")
async def get_signal_baselines(db: AsyncSession = Depends(db_session_dependency)) -> dict[str, Any]:
    configs = (await db.execute(select(SignalBaselineConfiguration).order_by(SignalBaselineConfiguration.created_at.desc()))).scalars().all()
    return {"status": await baseline_status(db), "configurations": [_baseline_payload(config) for config in configs]}


@router.post("/signal-baselines/recompute")
async def recompute_signal_baselines(
    db: AsyncSession = Depends(db_session_dependency),
) -> dict[str, Any]:
    try:
        config = await build_signal_baseline(db, "bootstrap-admin")
    except ValueError as exc:
        raise APIError(409, "insufficient_distribution_data", str(exc)) from exc
    return _baseline_payload(config)


@router.post("/signal-baselines/{configuration_id}/activate")
async def activate_signal_baseline(
    configuration_id: int,
    payload: ActivateSignalBaselineRequest,
    db: AsyncSession = Depends(db_session_dependency),
) -> dict[str, Any]:
    config = await db.get(SignalBaselineConfiguration, configuration_id)
    if config is None:
        raise APIError(404, "not_found", "Signal baseline configuration not found.")
    await db.execute(SignalBaselineConfiguration.__table__.update().where(SignalBaselineConfiguration.is_active.is_(True)).values(is_active=False))
    config.is_active = True
    config.activated_by = "bootstrap-admin"
    from datetime import UTC, datetime
    config.activated_at = datetime.now(UTC)
    await db.commit()
    return {**_baseline_payload(config), "activation_reason": payload.reason}


def _baseline_payload(config: SignalBaselineConfiguration) -> dict[str, Any]:
    return {"id": config.id, "version": config.version, "sample_size": config.sample_size, "is_active": config.is_active, "baselines": config.baselines, "distribution_summary": config.distribution_summary, "created_at": config.created_at.isoformat()}
