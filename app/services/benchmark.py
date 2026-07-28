from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Audit
from app.services.scoring_constants import PERCENTILE_COLD_START_SAMPLE_SIZE, SCHEMA_VERSION


@dataclass(frozen=True)
class PercentileBenchmark:
    percentile: int
    sample_size: int
    cold_start: bool


async def calculate_percentile_benchmark(
    db: AsyncSession,
    *,
    username: str,
    scores: dict[str, int],
    account_age_months: int,
) -> PercentileBenchmark:
    lower_age, upper_age = _age_cohort(account_age_months)
    latest_ids = (
        select(func.max(Audit.id).label("id"))
        .where(
            Audit.schema_version == SCHEMA_VERSION,
            Audit.account_age_months.is_not(None),
            Audit.username != username.lower(),
        )
        .group_by(Audit.username)
        .subquery()
    )
    query = select(
        Audit.profile_strength,
        Audit.project_depth,
        Audit.commit_consistency,
        Audit.tech_diversity,
    ).where(Audit.id.in_(select(latest_ids.c.id)), Audit.account_age_months >= lower_age)
    if upper_age is not None:
        query = query.where(Audit.account_age_months < upper_age)

    rows = (await db.execute(query)).all()
    historical_scores = [
        _composite_average(
            {
                "profile_strength": row.profile_strength,
                "project_depth": row.project_depth,
                "commit_consistency": row.commit_consistency,
                "tech_diversity": row.tech_diversity,
            }
        )
        for row in rows
    ]
    target = _composite_average(scores)
    below = sum(value < target for value in historical_scores)
    tied = sum(value == target for value in historical_scores)
    sample_size = len(historical_scores)

    # Midrank includes the current profile itself, yielding an honest 50th
    # percentile when no comparable historical audits exist yet.
    percentile = round(100 * (below + (tied * 0.5) + 0.5) / (sample_size + 1))
    return PercentileBenchmark(
        percentile=max(1, min(99, percentile)),
        sample_size=sample_size,
        cold_start=sample_size < PERCENTILE_COLD_START_SAMPLE_SIZE,
    )


def apply_percentile_benchmark(scores_entry: dict, benchmark: PercentileBenchmark) -> None:
    scores_entry["scores"]["percentile_benchmark"] = benchmark.percentile
    scores_entry["percentile_sample_size"] = benchmark.sample_size
    scores_entry["percentile_cold_start"] = benchmark.cold_start


def _composite_average(scores: dict[str, int]) -> float:
    keys = ("profile_strength", "project_depth", "commit_consistency", "tech_diversity")
    return sum(scores[key] for key in keys) / len(keys)


def _age_cohort(account_age_months: int) -> tuple[int, int | None]:
    if account_age_months < 12:
        return 0, 12
    if account_age_months < 36:
        return 12, 36
    if account_age_months < 72:
        return 36, 72
    return 72, None
