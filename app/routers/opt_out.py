from fastapi import APIRouter, Depends, Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Audit, OptedOutUsername, ReviewQueueItem
from app.dependencies import cache_client_dependency, db_session_dependency, rate_limiters_dependency
from app.models.api import OptOutRequest
from app.services.cache import purge_audit_cache
from app.services.rate_limit import RateLimiterRegistry
from app.services.scoring_constants import SCHEMA_VERSION

router = APIRouter(prefix="/api/v1")


@router.post("/opt-out")
async def post_opt_out(
    payload: OptOutRequest,
    request: Request,
    db: AsyncSession = Depends(db_session_dependency),
    cache_client=Depends(cache_client_dependency),
    rate_limiters: RateLimiterRegistry = Depends(rate_limiters_dependency),
) -> dict[str, str]:
    await rate_limiters.check("opt_out", request)
    username = payload.username.lower()
    await db.merge(OptedOutUsername(username=username))
    audit_ids = select(Audit.id).where(Audit.username == username)
    await db.execute(delete(ReviewQueueItem).where(ReviewQueueItem.audit_id.in_(audit_ids)))
    await db.execute(delete(Audit).where(Audit.username == username))
    await db.commit()
    await purge_audit_cache(cache_client, username, SCHEMA_VERSION)
    return {"status": "opted_out"}


@router.delete("/opt-out/{username}")
async def delete_opt_out(
    username: str,
    request: Request,
    db: AsyncSession = Depends(db_session_dependency),
    rate_limiters: RateLimiterRegistry = Depends(rate_limiters_dependency),
) -> dict[str, str]:
    await rate_limiters.check("opt_out", request)
    await db.execute(delete(OptedOutUsername).where(OptedOutUsername.username == username.lower()))
    await db.commit()
    return {"status": "active"}
