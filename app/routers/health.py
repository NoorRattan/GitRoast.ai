from fastapi import APIRouter

from app.services.scoring_constants import SCHEMA_VERSION

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/v1/health")
async def api_health() -> dict[str, str | int]:
    return {"status": "ok", "schema_version": SCHEMA_VERSION}
