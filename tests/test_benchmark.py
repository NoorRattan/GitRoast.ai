from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Audit, Base
from app.services.benchmark import calculate_percentile_benchmark
from app.services.scoring_constants import SCHEMA_VERSION


def _audit(username: str, score: int, account_age_months: int) -> Audit:
    return Audit(
        username=username,
        profile_strength=score,
        project_depth=score,
        commit_consistency=score,
        tech_diversity=score,
        percentile_benchmark=50,
        account_age_months=account_age_months,
        schema_version=SCHEMA_VERSION,
    )


async def test_percentile_uses_latest_profiles_in_same_age_cohort():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        db.add_all(
            [
                _audit("low", 20, 24),
                _audit("middle", 40, 25),
                _audit("high", 60, 30),
                _audit("other-cohort", 100, 80),
                _audit("current", 99, 24),
            ]
        )
        await db.commit()
        result = await calculate_percentile_benchmark(
            db,
            username="current",
            scores={
                "profile_strength": 50,
                "project_depth": 50,
                "commit_consistency": 50,
                "tech_diversity": 50,
                "percentile_benchmark": 50,
            },
            account_age_months=24,
        )

    await engine.dispose()
    assert result.percentile == 62
    assert result.sample_size == 3
    assert result.cold_start is True


async def test_percentile_is_neutral_and_explicit_during_empty_cold_start():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        result = await calculate_percentile_benchmark(
            db,
            username="first",
            scores={
                "profile_strength": 80,
                "project_depth": 80,
                "commit_consistency": 80,
                "tech_diversity": 80,
                "percentile_benchmark": 50,
            },
            account_age_months=6,
        )

    await engine.dispose()
    assert result.percentile == 50
    assert result.sample_size == 0
    assert result.cold_start is True
