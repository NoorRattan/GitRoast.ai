from datetime import UTC, datetime

from app.services.github_client import parse_profile_response
from app.services.scoring import _compute_metrics, _is_generic_commit_message, _readme_score, score_profile
from app.services.scoring_constants import COMPOSITE_SCORE_KEYS, FindingMetric


NOW = datetime(2026, 7, 26, tzinfo=UTC)


def _score(load_github_fixture, fixture_name):
    profile = parse_profile_response(load_github_fixture(fixture_name))
    return score_profile(profile, now=NOW)


def test_beginner_fixture_trips_beginner_account(load_github_fixture):
    result = _score(load_github_fixture, "beginner_account.json")

    assert result["flags"]["beginner_account"] is True


def test_small_fixture_is_not_beginner(load_github_fixture):
    result = _score(load_github_fixture, "small_profile.json")

    assert result["flags"]["beginner_account"] is False


def test_forked_only_fixture_has_high_fork_penalty_and_low_project_depth(load_github_fixture):
    result = _score(load_github_fixture, "forked_only.json")

    findings = {item["metric"]: item for item in result["findings"]}
    assert findings["fork_ratio"]["value"] == 1.0
    assert result["scores"]["project_depth"] < 35


def test_findings_are_capped_and_schema_constrained(load_github_fixture):
    result = _score(load_github_fixture, "whale_profile.json")
    allowed_metrics = {metric.value for metric in FindingMetric}

    assert len(result["findings"]) <= 6
    assert all(item["metric"] in allowed_metrics for item in result["findings"])
    assert all(item["contributes_to"] in COMPOSITE_SCORE_KEYS for item in result["findings"])


def test_all_finding_metrics_are_producible_across_fixtures(load_github_fixture):
    produced = set()
    for fixture_name in [
        "small_profile.json",
        "whale_profile.json",
        "beginner_account.json",
        "forked_only.json",
    ]:
        produced.update(item["metric"] for item in _score(load_github_fixture, fixture_name)["findings"])

    assert produced == {metric.value for metric in FindingMetric}


def test_active_weeks_ratio_uses_oldest_default_branch_commit_bound():
    recent_profile = {
        "username": "longrunner",
        "created_at": "2019-01-01T00:00:00Z",
        "external_pr_count": 2,
        "repos": [
            {
                "name": "flagship",
                "is_fork": False,
                "has_license": True,
                "disk_usage": 2000,
                "stargazer_count": 0,
                "is_pinned": True,
                "languages": {"Python": 1000},
                "commit_count": 500,
                "commit_messages": ["Add production verification checklist"],
                "commit_dates": ["2026-07-20T00:00:00Z"],
                "first_commit_date": "2020-01-01T00:00:00Z",
                "root_entries": [{"name": "tests", "type": "tree"}],
                "readme_fetched": True,
                "readme_text": "Installation\nUsage\nDemo\n![demo](demo.png)\n![badge](badge.svg)",
                "has_coverage_badge": True,
            }
        ],
    }
    truncated_profile = {
        **recent_profile,
        "repos": [{key: value for key, value in recent_profile["repos"][0].items() if key != "first_commit_date"}],
    }

    bounded = score_profile(recent_profile, now=NOW)
    truncated = score_profile(truncated_profile, now=NOW)

    assert bounded["scores"]["commit_consistency"] < truncated["scores"]["commit_consistency"]
    finding = next(item for item in bounded["findings"] if item["metric"] == "active_weeks_ratio")
    assert "oldest default-branch commit" in finding["detail"]


def test_readme_score_uses_markdown_headings_and_ignores_incidental_keywords():
    headed = [{"readme_fetched": True, "readme_text": "## Quick Start\n## Examples\n## Demo\n"}]
    incidental = [{"readme_fetched": True, "readme_text": "This sentence mentions installation, usage, and demo without sections."}]

    assert _readme_score(headed) > _readme_score(incidental)


def test_conventional_commit_messages_are_not_generic_even_when_short():
    assert _is_generic_commit_message("fix: null check") is False
    assert _is_generic_commit_message("feat(api)!: protect audit route") is False
    assert _is_generic_commit_message("fix") is True
    assert _is_generic_commit_message("wip") is True


def test_substantial_one_commit_repository_is_not_counted_as_graveyard():
    profile = {
        "created_at": "2020-01-01T00:00:00Z",
        "external_pr_count": 1,
        "repos": [
            {
                "name": "shipped-tool",
                "is_fork": False,
                "commit_count": 1,
                "disk_usage": 50_000,
                "commit_messages": ["feat: ship complete tool"],
                "commit_dates": ["2026-07-01T00:00:00Z"],
                "languages": {"Python": 50_000},
            },
            {
                "name": "abandoned-stub",
                "is_fork": False,
                "commit_count": 1,
                "disk_usage": 10,
                "commit_messages": ["wip"],
                "commit_dates": ["2026-07-01T00:00:00Z"],
                "languages": {"Python": 10},
            },
        ],
    }

    metrics = _compute_metrics(profile, profile["repos"], NOW)

    assert metrics["graveyard_ratio"] == 0.5
