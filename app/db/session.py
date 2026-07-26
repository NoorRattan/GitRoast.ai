from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: Settings | None = None, database_url: str | None = None) -> async_sessionmaker[AsyncSession]:
    global _engine, _session_factory
    url = database_url or (settings.neon_database_url if settings else None)
    if not url:
        raise ValueError("database_url or settings is required")
    if _engine is None:
        _engine = create_async_engine(url, pool_pre_ping=True)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_factory


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("database session factory has not been initialized")
    return _session_factory


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
