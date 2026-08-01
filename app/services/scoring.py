from collections import Counter
from datetime import UTC, datetime
import math
import re
from typing import Any

from app.services.scoring_constants import (
    ACTIVE_WEEKS_WEIGHT,
    BEGINNER_ACCOUNT_MAX_AGE_MONTHS,
    BEGINNER_MIN_EXTERNAL_PRS,
    BEGINNER_MIN_ORIGINAL_REPOS,
    BEGINNER_MIN_TOTAL_COMMITS,
    COMPOSITE_SCORE_KEYS,
    DESCRIPTIVE_MESSAGES_WEIGHT,
    FindingMetric,
    GENERIC_COMMIT_MESSAGE_PATTERNS,
    GENERIC_COMMIT_MIN_LENGTH,
    GREEN_SQUARE_FARMING_THRESHOLD,
    HEALTHY_BASELINES,
    SCHEMA_VERSION,
    TRIVIAL_REPO_MAX_COMMITS,
    TRIVIAL_REPO_MAX_DISK_USAGE_KB,
)


GENERIC_MESSAGE_REGEXES = tuple(re.compile(pattern, re.IGNORECASE) for pattern in GENERIC_COMMIT_MESSAGE_PATTERNS)
CONVENTIONAL_COMMIT_REGEX = re.compile(
    r"^(?:build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(?:\([^)\r\n]+\))?!?:\s+\S",
    re.IGNORECASE,
)


def score_profile(profile: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    repos = profile.get("repos", [])
    original_repos = [repo for repo in repos if not repo.get("is_fork")]
    metrics = _compute_metrics(profile, original_repos, now)

    scores = {
        "profile_strength": _profile_strength(metrics),
        "project_depth": _project_depth(metrics),
        "commit_consistency": _commit_consistency(metrics),
        "tech_diversity": _tech_diversity(metrics),
        # Replaced by the DB-backed cohort benchmark in the request pipeline.
        # A single-profile empirical distribution has a neutral midpoint rank.
        "percentile_benchmark": 50,
    }

    flags = {
        "green_square_farming": metrics["green_square_farming_ratio"] > GREEN_SQUARE_FARMING_THRESHOLD,
        "beginner_account": _is_beginner(metrics),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "scores": scores,
        "flags": flags,
        "findings": _findings(metrics),
        "avatar_url": profile.get("avatar_url"),
        "account_age_months": metrics["account_age_months"],
        "percentile_sample_size": 0,
        "percentile_cold_start": True,
    }


def _compute_metrics(profile: dict[str, Any], original_repos: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    repos = profile.get("repos", [])
    total_repos = len(repos)
    original_count = len(original_repos)
    total_commits = sum(int(repo.get("commit_count", 0)) for repo in original_repos)
    commit_messages = [message for repo in original_repos for message in repo.get("commit_messages", [])]
    commit_dates = [_parse_datetime(date) for repo in original_repos for date in repo.get("commit_dates", [])]
    commit_dates = [date for date in commit_dates if date is not None]
    first_commit_bounds = [_parse_datetime(repo.get("first_commit_date")) for repo in original_repos]
    first_commit_bounds = [date for date in first_commit_bounds if date is not None]
    first_commit_candidates = commit_dates + first_commit_bounds
    first_commit = min(first_commit_candidates) if first_commit_candidates else None
    weeks_since_first = max(1, math.ceil(((now - first_commit).days if first_commit else 0) / 7))
    active_weeks = len({date.isocalendar()[:2] for date in commit_dates})

    generic_messages = [message for message in commit_messages if _is_generic_commit_message(message)]
    graveyard_repos = [
        repo
        for repo in original_repos
        if int(repo.get("commit_count", 0)) <= 1
        and int(repo.get("disk_usage", 0)) <= TRIVIAL_REPO_MAX_DISK_USAGE_KB
    ]
    trivial_commits = sum(
        int(repo.get("commit_count", 0))
        for repo in original_repos
        if int(repo.get("disk_usage", 0)) <= TRIVIAL_REPO_MAX_DISK_USAGE_KB
        and int(repo.get("commit_count", 0)) <= TRIVIAL_REPO_MAX_COMMITS
    )

    languages = Counter()
    for repo in original_repos:
        languages.update({name: int(size) for name, size in repo.get("languages", {}).items()})
    language_total = sum(languages.values())
    largest_language_ratio = max(languages.values(), default=0) / language_total if language_total else 1.0

    return {
        "account_age_months": _account_age_months(profile.get("created_at"), now),
        "total_repos": total_repos,
        "original_repos": original_count,
        "fork_ratio": _safe_ratio(total_repos - original_count, total_repos),
        "license_coverage": _safe_ratio(sum(1 for repo in original_repos if repo.get("has_license")), original_count),
        "readme_score": _readme_score(original_repos),
        "pinned_curation_score": _pinned_curation_score(original_repos),
        "pinned_curation_mismatch": 1.0 - _pinned_curation_score(original_repos),
        "repo_substance_score": _repo_substance_score(original_repos),
        "ci_hygiene_score": _ci_hygiene_score(original_repos),
        "ci_hygiene_gap": 1.0 - _ci_hygiene_score(original_repos),
        "graveyard_ratio": _safe_ratio(len(graveyard_repos), original_count),
        "active_weeks_ratio": _safe_ratio(active_weeks, weeks_since_first),
        "first_commit_bound_available": bool(first_commit_bounds),
        "generic_commit_ratio": _safe_ratio(len(generic_messages), len(commit_messages)),
        "total_commits": total_commits,
        "external_pr_count": int(profile.get("external_pr_count", 0)),
        "green_square_farming_ratio": _safe_ratio(trivial_commits, total_commits),
        "language_count": len(languages),
        "largest_language_ratio": largest_language_ratio,
        "stack_bonus": _stack_bonus(set(languages)),
    }


def _commit_consistency(metrics: dict[str, Any]) -> int:
    score = (
        metrics["active_weeks_ratio"] * ACTIVE_WEEKS_WEIGHT
        + (1 - metrics["generic_commit_ratio"]) * DESCRIPTIVE_MESSAGES_WEIGHT
    )
    return _as_score(score)


def _profile_strength(metrics: dict[str, Any]) -> int:
    score = (
        metrics["readme_score"] * 0.35
        + metrics["pinned_curation_score"] * 0.25
        + (1 - metrics["fork_ratio"]) * 0.2
        + metrics["license_coverage"] * 0.2
    )
    return _as_score(score)


def _project_depth(metrics: dict[str, Any]) -> int:
    score = (
        metrics["repo_substance_score"] * 0.45
        + metrics["ci_hygiene_score"] * 0.25
        + (1 - metrics["graveyard_ratio"]) * 0.3
    )
    return _as_score(score)


def _tech_diversity(metrics: dict[str, Any]) -> int:
    distinct_score = min(metrics["language_count"] / 5, 1.0)
    concentration_score = 1 - max(0.0, metrics["largest_language_ratio"] - 0.55) / 0.45
    score = distinct_score * 0.45 + concentration_score * 0.35 + metrics["stack_bonus"] * 0.2
    return _as_score(score)


def _findings(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [
        _finding(FindingMetric.graveyard_ratio, metrics["graveyard_ratio"], "project_depth", f"{metrics['graveyard_ratio']:.0%} of original repos have one commit or less"),
        _finding(FindingMetric.generic_commit_ratio, metrics["generic_commit_ratio"], "commit_consistency", f"{metrics['generic_commit_ratio']:.0%} of sampled commit messages are generic"),
        _finding(FindingMetric.active_weeks_ratio, metrics["active_weeks_ratio"], "commit_consistency", _active_weeks_detail(metrics)),
        _finding(FindingMetric.fork_ratio, metrics["fork_ratio"], "profile_strength", f"{metrics['fork_ratio']:.0%} of visible repos are forks"),
        _finding(FindingMetric.license_coverage, metrics["license_coverage"], "profile_strength", f"{metrics['license_coverage']:.0%} of original repos include license metadata"),
        _finding(FindingMetric.pinned_curation_mismatch, metrics["pinned_curation_mismatch"], "profile_strength", f"Pinned repos match {1 - metrics['pinned_curation_mismatch']:.0%} of the strongest visible repos"),
        _finding(FindingMetric.readme_heuristic_gaps, 1 - metrics["readme_score"], "profile_strength", f"README heuristics cover {metrics['readme_score']:.0%} of expected presentation signals"),
        _finding(FindingMetric.tech_diversity_concentration, metrics["largest_language_ratio"], "tech_diversity", f"The largest language accounts for {metrics['largest_language_ratio']:.0%} of measured code bytes"),
        _finding(FindingMetric.repo_substance_score, metrics["repo_substance_score"], "project_depth", f"Repo substance proxy scores {metrics['repo_substance_score']:.0%} across original repos"),
        _finding(FindingMetric.ci_hygiene_gap, metrics["ci_hygiene_gap"], "project_depth", f"CI and test hygiene is missing in {metrics['ci_hygiene_gap']:.0%} of expected signals"),
    ]
    candidates.sort(key=lambda item: item["_deviation"], reverse=True)
    return [{key: value for key, value in item.items() if key != "_deviation"} for item in candidates[:6]]


def _active_weeks_detail(metrics: dict[str, Any]) -> str:
    if metrics["first_commit_bound_available"]:
        return f"Sampled activity appears in {metrics['active_weeks_ratio']:.0%} of weeks since the oldest default-branch commit"
    return f"Activity appears in {metrics['active_weeks_ratio']:.0%} of weeks since the first sampled commit"


def _finding(metric: FindingMetric, value: float, contributes_to: str, detail: str) -> dict[str, Any]:
    if contributes_to not in COMPOSITE_SCORE_KEYS:
        raise ValueError(f"invalid composite key: {contributes_to}")
    baseline = HEALTHY_BASELINES[metric]
    return {
        "metric": metric.value,
        "detail": detail,
        "value": round(value, 4),
        "contributes_to": contributes_to,
        "_deviation": abs(value - baseline),
    }


def _readme_score(repos: list[dict[str, Any]]) -> float:
    sampled_repos = [repo for repo in repos if repo.get("readme_fetched")]
    if not sampled_repos:
        return 0.0
    scores = []
    for repo in sampled_repos:
        readme = str(repo.get("readme_text", ""))
        lower = readme.lower()
        headings = _markdown_headings(readme)
        header_score = sum(
            (
                _has_heading(headings, ("installation", "install", "setup", "getting started", "quick start")),
                _has_heading(headings, ("usage", "how to use", "run", "running", "examples")),
                _has_heading(headings, ("demo", "preview", "screenshots")),
            )
        ) / 3
        length_score = min(len(readme) / 1200, 1.0)
        image_score = 1.0 if re.search(r"!\[[^\]]*]\([^)]+\.(png|jpg|jpeg|gif|webp)", readme, re.I) else 0.0
        badge_score = 1.0 if "shields.io" in lower or "badge" in lower else 0.0
        scores.append(header_score * 0.35 + length_score * 0.3 + image_score * 0.2 + badge_score * 0.15)
    return sum(scores) / len(scores)


def _pinned_curation_score(repos: list[dict[str, Any]]) -> float:
    if not repos:
        return 0.0
    pinned = {repo["name"] for repo in repos if repo.get("is_pinned") and repo.get("name")}
    if not pinned:
        return 0.0
    ranked = sorted(
        repos,
        key=lambda repo: (int(repo.get("stargazer_count", 0)), int(repo.get("commit_count", 0)), int(repo.get("disk_usage", 0))),
        reverse=True,
    )
    strongest = {repo["name"] for repo in ranked[: len(pinned)] if repo.get("name")}
    return len(pinned & strongest) / len(pinned)


def _repo_substance_score(repos: list[dict[str, Any]]) -> float:
    if not repos:
        return 0.0
    scores = []
    for repo in repos:
        commit_score = min(int(repo.get("commit_count", 0)) / 25, 1.0)
        disk_score = min(int(repo.get("disk_usage", 0)) / 750, 1.0)
        scores.append(commit_score * 0.55 + disk_score * 0.45)
    return sum(scores) / len(scores)


def _ci_hygiene_score(repos: list[dict[str, Any]]) -> float:
    if not repos:
        return 0.0
    scores = []
    for repo in repos:
        entries = {entry.get("name", "").lower() for entry in repo.get("root_entries", [])}
        workflows = ".github" in entries
        test_dir = bool(entries & {"tests", "test", "__tests__", "spec"})
        coverage = bool(repo.get("has_coverage_badge")) or "codecov.yml" in entries or ".coveragerc" in entries
        scores.append((workflows + test_dir + coverage) / 3)
    return sum(scores) / len(scores)


def _stack_bonus(languages: set[str]) -> float:
    frontend = bool(languages & {"TypeScript", "JavaScript", "HTML", "CSS"})
    backend = bool(languages & {"Python", "Go", "Rust", "Java", "C#", "Ruby", "PHP"})
    infra = bool(languages & {"Dockerfile", "HCL", "Shell", "Makefile", "YAML"})
    return (frontend + backend + infra) / 3


def _is_beginner(metrics: dict[str, Any]) -> bool:
    return (
        metrics["account_age_months"] < BEGINNER_ACCOUNT_MAX_AGE_MONTHS
        or metrics["original_repos"] < BEGINNER_MIN_ORIGINAL_REPOS
        or metrics["total_commits"] < BEGINNER_MIN_TOTAL_COMMITS
        or metrics["external_pr_count"] < BEGINNER_MIN_EXTERNAL_PRS
    )


def _is_generic_commit_message(message: str) -> bool:
    stripped = message.strip()
    if CONVENTIONAL_COMMIT_REGEX.match(stripped):
        return False
    if len(stripped) < GENERIC_COMMIT_MIN_LENGTH:
        return True
    return any(pattern.search(stripped) for pattern in GENERIC_MESSAGE_REGEXES)


def _markdown_headings(markdown: str) -> list[str]:
    return [heading.strip().lower() for heading in re.findall(r"(?m)^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", markdown)]


def _has_heading(headings: list[str], terms: tuple[str, ...]) -> bool:
    return any(any(term in heading for term in terms) for heading in headings)


def _account_age_months(created_at: str | None, now: datetime) -> int:
    created = _parse_datetime(created_at)
    if created is None:
        return 0
    return max(0, (now.year - created.year) * 12 + now.month - created.month)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    if denominator <= 0:
        return 0.0
    return max(0.0, min(float(numerator) / float(denominator), 1.0))


def _as_score(value: float) -> int:
    return max(0, min(100, round(value * 100)))
