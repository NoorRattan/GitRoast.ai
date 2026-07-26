from datetime import UTC, datetime

from app.services.github_client import parse_profile_response
from app.services.scoring import score_profile
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
