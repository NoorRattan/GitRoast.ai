from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Audit, Base
from app.services.signal_baselines import build_signal_baseline, derive_baselines
from app.services.scoring_constants import DISTRIBUTIONAL_BASELINE_MIN_SAMPLE_SIZE, FindingMetric, SCHEMA_VERSION


def test_distributional_baselines_use_directional_percentiles():
    snapshots = [
        {"graveyard_ratio": value / 100, "generic_commit_ratio": value / 100, "active_weeks_ratio": value / 100, "fork_ratio": value / 100, "license_coverage": value / 100, "pinned_curation_mismatch": value / 100, "readme_score": value / 100, "largest_language_ratio": value / 100, "repo_substance_score": value / 100, "ci_hygiene_gap": value / 100}
        for value in range(100)
    ]

    baselines, summary = derive_baselines(snapshots)

    assert baselines[FindingMetric.graveyard_ratio] < 0.30
    assert baselines[FindingMetric.active_weeks_ratio] > 0.70
    assert baselines[FindingMetric.readme_heuristic_gaps] < 0.30
    assert summary["repo_substance_score"]["median"] == 0.495


async def test_baseline_build_refuses_small_or_non_distinct_population():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    snapshot = {"graveyard_ratio": 0.1, "generic_commit_ratio": 0.1, "active_weeks_ratio": 0.8, "fork_ratio": 0.1, "license_coverage": 0.8, "pinned_curation_mismatch": 0.1, "readme_score": 0.8, "largest_language_ratio": 0.5, "repo_substance_score": 0.8, "ci_hygiene_gap": 0.1}
    async with session_factory() as db:
        db.add_all([
            Audit(username=f"user-{index}", profile_strength=70, project_depth=70, commit_consistency=70, tech_diversity=70, percentile_benchmark=50, account_age_months=12, schema_version=SCHEMA_VERSION, metric_snapshot=snapshot)
            for index in range(DISTRIBUTIONAL_BASELINE_MIN_SAMPLE_SIZE - 1)
        ])
        await db.commit()
        try:
            await build_signal_baseline(db, "admin")
        except ValueError as exc:
            assert "Need" in str(exc)
        else:
            raise AssertionError("baseline build must reject a small population")
    await engine.dispose()


async def test_baseline_build_creates_an_inactive_version_from_distinct_profiles():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        for index in range(DISTRIBUTIONAL_BASELINE_MIN_SAMPLE_SIZE):
            value = index / DISTRIBUTIONAL_BASELINE_MIN_SAMPLE_SIZE
            snapshot = {"graveyard_ratio": value, "generic_commit_ratio": value, "active_weeks_ratio": 1 - value, "fork_ratio": value, "license_coverage": 1 - value, "pinned_curation_mismatch": value, "readme_score": 1 - value, "largest_language_ratio": value, "repo_substance_score": 1 - value, "ci_hygiene_gap": value}
            db.add(Audit(username=f"profile-{index}", profile_strength=70, project_depth=70, commit_consistency=70, tech_diversity=70, percentile_benchmark=50, account_age_months=12, schema_version=SCHEMA_VERSION, metric_snapshot=snapshot))
        await db.commit()
        config = await build_signal_baseline(db, "admin")

    await engine.dispose()
    assert config.sample_size == DISTRIBUTIONAL_BASELINE_MIN_SAMPLE_SIZE
    assert config.is_active is False
    assert config.baselines["active_weeks_ratio"] > 0.70
