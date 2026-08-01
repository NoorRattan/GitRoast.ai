"""Population-grounded finding baselines, never a substitute for human quality labels."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Audit, SignalBaselineConfiguration
from app.services.scoring_constants import DISTRIBUTIONAL_BASELINE_MIN_SAMPLE_SIZE, FindingMetric, HEALTHY_BASELINES, SCHEMA_VERSION

SNAPSHOT_KEY_FOR_FINDING = {
    FindingMetric.graveyard_ratio: ("graveyard_ratio", 0.25),
    FindingMetric.generic_commit_ratio: ("generic_commit_ratio", 0.25),
    FindingMetric.active_weeks_ratio: ("active_weeks_ratio", 0.75),
    FindingMetric.fork_ratio: ("fork_ratio", 0.25),
    FindingMetric.license_coverage: ("license_coverage", 0.75),
    FindingMetric.pinned_curation_mismatch: ("pinned_curation_mismatch", 0.25),
    FindingMetric.readme_heuristic_gaps: ("readme_score", 0.75),
    FindingMetric.tech_diversity_concentration: ("largest_language_ratio", 0.25),
    FindingMetric.repo_substance_score: ("repo_substance_score", 0.75),
    FindingMetric.ci_hygiene_gap: ("ci_hygiene_gap", 0.25),
}


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("cannot calculate a percentile of an empty set")
    position = (len(ordered) - 1) * fraction
    lower, upper = int(position), min(int(position) + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def derive_baselines(snapshots: list[dict[str, Any]]) -> tuple[dict[FindingMetric, float], dict[str, dict[str, float]]]:
    result: dict[FindingMetric, float] = {}
    summary: dict[str, dict[str, float]] = {}
    for finding, (key, target_percentile) in SNAPSHOT_KEY_FOR_FINDING.items():
        values = [float(snapshot[key]) for snapshot in snapshots if key in snapshot]
        if not values:
            result[finding] = HEALTHY_BASELINES[finding]
            continue
        raw = percentile(values, target_percentile)
        baseline = 1 - raw if finding == FindingMetric.readme_heuristic_gaps else raw
        result[finding] = round(max(0.0, min(1.0, baseline)), 4)
        summary[key] = {"p25": round(percentile(values, 0.25), 4), "median": round(percentile(values, 0.5), 4), "p75": round(percentile(values, 0.75), 4)}
    return result, summary


async def latest_signal_baseline(db: AsyncSession) -> SignalBaselineConfiguration | None:
    return (await db.execute(select(SignalBaselineConfiguration).where(SignalBaselineConfiguration.is_active.is_(True)).order_by(SignalBaselineConfiguration.activated_at.desc(), SignalBaselineConfiguration.id.desc()).limit(1))).scalar_one_or_none()


async def baseline_status(db: AsyncSession) -> dict[str, Any]:
    active = await latest_signal_baseline(db)
    latest_ids = select(func.max(Audit.id).label("id")).where(Audit.schema_version == SCHEMA_VERSION, Audit.metric_snapshot.is_not(None)).group_by(Audit.username).subquery()
    sample_size = int((await db.execute(select(func.count()).select_from(Audit).where(Audit.id.in_(select(latest_ids.c.id))))).scalar_one())
    return {"status": "active" if active else "collecting", "version": active.version if active else "hand-tuned-v1", "sample_size": sample_size, "minimum_sample_size": DISTRIBUTIONAL_BASELINE_MIN_SAMPLE_SIZE}


async def build_signal_baseline(db: AsyncSession, actor: str) -> SignalBaselineConfiguration:
    latest_ids = select(func.max(Audit.id).label("id")).where(Audit.schema_version == SCHEMA_VERSION, Audit.metric_snapshot.is_not(None)).group_by(Audit.username).subquery()
    snapshots = list((await db.execute(select(Audit.metric_snapshot).where(Audit.id.in_(select(latest_ids.c.id))))).scalars().all())
    if len(snapshots) < DISTRIBUTIONAL_BASELINE_MIN_SAMPLE_SIZE:
        raise ValueError(f"Need {DISTRIBUTIONAL_BASELINE_MIN_SAMPLE_SIZE} distinct evidence snapshots; found {len(snapshots)}")
    baselines, summary = derive_baselines(snapshots)
    version = f"population-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    config = SignalBaselineConfiguration(version=version, source_schema_version=SCHEMA_VERSION, sample_size=len(snapshots), baselines={metric.value: value for metric, value in baselines.items()}, distribution_summary=summary, is_active=False, activated_by=actor)
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


def config_baselines(config: SignalBaselineConfiguration | None) -> dict[FindingMetric, float]:
    if config is None:
        return dict(HEALTHY_BASELINES)
    return {metric: float(config.baselines[metric.value]) for metric in FindingMetric}
