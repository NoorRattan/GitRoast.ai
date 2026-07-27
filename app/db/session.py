from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.db.models import Base

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: Settings | None = None, database_url: str | None = None) -> async_sessionmaker[AsyncSession]:
    global _engine, _session_factory
    url = database_url or (settings.neon_database_url if settings else None)
    if not url:
        raise ValueError("database_url or settings is required")
    if _engine is None:
        normalized_url, connect_args = async_database_engine_options(url)
        _engine = create_async_engine(normalized_url, pool_pre_ping=True, connect_args=connect_args)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_factory


def async_database_engine_options(database_url: str) -> tuple[str, dict[str, object]]:
    url = make_url(database_url)
    connect_args: dict[str, object] = {}

    if url.drivername == "postgresql":
        query = dict(url.query)
        sslmode = query.pop("sslmode", None)
        query.pop("channel_binding", None)
        url = url.set(drivername="postgresql+asyncpg", query=query)
        if sslmode in {"require", "verify-ca", "verify-full"}:
            connect_args["ssl"] = True

    return url.render_as_string(hide_password=False), connect_args


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("database session factory has not been initialized")
    return _session_factory


async def ensure_db_schema() -> None:
    if _engine is None:
        raise RuntimeError("database engine has not been initialized")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
