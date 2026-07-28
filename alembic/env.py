import asyncio
from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.models import Base
from app.db.session import async_database_engine_options


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_options() -> tuple[str, dict[str, object]]:
    database_url = os.environ.get("NEON_DATABASE_URL")
    if not database_url:
        raise RuntimeError("NEON_DATABASE_URL is required to run database migrations")
    return async_database_engine_options(database_url)


def run_migrations_offline() -> None:
    database_url, _ = get_database_options()
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    database_url, connect_args = get_database_options()
    connectable = create_async_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
