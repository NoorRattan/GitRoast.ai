import json
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError
from app.core.security import require_admin
from app.db.models import ReviewQueueItem, ReviewStatus
from app.dependencies import db_session_dependency
from app.models.api import RejectReviewRequest, ReviewStatusValue

router = APIRouter(prefix="/api/v1/admin", dependencies=[Depends(require_admin)])


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
