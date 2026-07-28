from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.models import Base
from app.db.session import async_database_engine_options


def test_plain_postgres_url_is_normalized_for_asyncpg():
    url, connect_args = async_database_engine_options(
        "postgresql://user:pass@example.neon.tech/db?sslmode=require&channel_binding=require"
    )

    assert url == "postgresql+asyncpg://user:pass@example.neon.tech/db"
    assert connect_args == {"ssl": True}


def test_async_database_url_keeps_non_postgres_drivers():
    url, connect_args = async_database_engine_options("sqlite+aiosqlite:///:memory:")

    assert url == "sqlite+aiosqlite:///:memory:"
    assert connect_args == {}


async def test_db_schema_creates_expected_tables_and_columns():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def collect(sync_conn):
            inspector = inspect(sync_conn)
            return {
                table: {column["name"] for column in inspector.get_columns(table)}
                for table in inspector.get_table_names()
            }

        tables = await conn.run_sync(collect)

    await engine.dispose()

    assert {"audits", "opted_out_usernames", "review_queue"} <= set(tables)
    assert {
        "username",
        "profile_strength",
        "project_depth",
        "commit_consistency",
        "tech_diversity",
        "percentile_benchmark",
        "account_age_months",
        "schema_version",
        "created_at",
    } <= tables["audits"]
    assert {"username", "created_at"} <= tables["opted_out_usernames"]
    assert {"id", "audit_id", "generated_content", "review_status", "reason", "created_at"} <= tables["review_queue"]
