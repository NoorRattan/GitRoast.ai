from enum import StrEnum


SCHEMA_VERSION = 5

PERCENTILE_COLD_START_SAMPLE_SIZE = 20

ACTIVE_WEEKS_WEIGHT = 0.6
DESCRIPTIVE_MESSAGES_WEIGHT = 0.4

GENERIC_COMMIT_MESSAGE_PATTERNS = (
    r"^\s*fix\s*$",
    r"^\s*update\s*$",
    r"^\s*wip\s*$",
    r"^\s*asdf\s*$",
)
GENERIC_COMMIT_MIN_LENGTH = 10

BEGINNER_ACCOUNT_MAX_AGE_MONTHS = 6
BEGINNER_MIN_ORIGINAL_REPOS = 3
BEGINNER_MIN_TOTAL_COMMITS = 50
BEGINNER_MIN_EXTERNAL_PRS = 1

GREEN_SQUARE_FARMING_THRESHOLD = 0.55
TRIVIAL_REPO_MAX_DISK_USAGE_KB = 64
TRIVIAL_REPO_MAX_COMMITS = 3

CACHE_TTL_SECONDS = 6 * 60 * 60
STALE_REFRESH_WINDOW_SECONDS = 30 * 60


class FindingMetric(StrEnum):
    graveyard_ratio = "graveyard_ratio"
    generic_commit_ratio = "generic_commit_ratio"
    active_weeks_ratio = "active_weeks_ratio"
    fork_ratio = "fork_ratio"
    license_coverage = "license_coverage"
    pinned_curation_mismatch = "pinned_curation_mismatch"
    readme_heuristic_gaps = "readme_heuristic_gaps"
    tech_diversity_concentration = "tech_diversity_concentration"
    repo_substance_score = "repo_substance_score"
    ci_hygiene_gap = "ci_hygiene_gap"


COMPOSITE_SCORE_KEYS = frozenset(
    {
        "profile_strength",
        "project_depth",
        "commit_consistency",
        "tech_diversity",
        "percentile_benchmark",
    }
)

HEALTHY_BASELINES = {
    FindingMetric.graveyard_ratio: 0.05,
    FindingMetric.generic_commit_ratio: 0.15,
    FindingMetric.active_weeks_ratio: 0.65,
    FindingMetric.fork_ratio: 0.2,
    FindingMetric.license_coverage: 0.7,
    FindingMetric.pinned_curation_mismatch: 0.0,
    FindingMetric.readme_heuristic_gaps: 0.2,
    FindingMetric.tech_diversity_concentration: 0.55,
    FindingMetric.repo_substance_score: 0.75,
    FindingMetric.ci_hygiene_gap: 0.2,
}
