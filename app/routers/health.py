from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/v1/health")
async def api_health() -> dict[str, str]:
    return {"status": "ok"}
