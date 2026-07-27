import copy
import random

from app.services.roast_engine import (
    FALLBACK_STRENGTH,
    INTENSITIES,
    MIN_FINDING_TEMPLATES_PER_BUCKET,
    SUPPORTED_PLACEHOLDERS,
    generate_roast,
    load_line_bank,
    validate_line_bank,
)
from app.services.scoring_constants import FindingMetric


SCORES = {
    "profile_strength": 82,
    "project_depth": 76,
    "commit_consistency": 74,
    "tech_diversity": 88,
    "percentile_benchmark": 80,
}

FINDINGS = [
    {"metric": "graveyard_ratio", "detail": "3 of 8 original repos have one commit", "value": 0.375, "contributes_to": "project_depth"},
    {"metric": "generic_commit_ratio", "detail": "40% of commit messages are generic", "value": 0.4, "contributes_to": "commit_consistency"},
    {"metric": "fork_ratio", "detail": "5 of 12 visible repos are forks", "value": 0.4167, "contributes_to": "profile_strength"},
    {"metric": "ci_hygiene_gap", "detail": "CI is missing in 70% of expected signals", "value": 0.7, "contributes_to": "project_depth"},
]


def test_line_bank_schema_is_valid():
    dataset = load_line_bank()
    validate_line_bank(dataset)
    expected_metrics = {metric.value for metric in FindingMetric}

    assert set(dataset["finding_lines"]) == expected_metrics
    for metric in expected_metrics:
        assert set(dataset["finding_lines"][metric]) == set(INTENSITIES)
        for templates in dataset["finding_lines"][metric].values():
            assert len(templates) >= MIN_FINDING_TEMPLATES_PER_BUCKET
            assert all("{" not in template or any(f"{{{name}}}" in template for name in SUPPORTED_PLACEHOLDERS) for template in templates)
        assert dataset["strength_lines"][metric]
        assert dataset["roadmap_actions"][metric]


def test_generate_roast_is_seed_deterministic():
    first = generate_roast(copy.deepcopy(FINDINGS), SCORES, "brutal", rng=random.Random(42))
    second = generate_roast(copy.deepcopy(FINDINGS), SCORES, "brutal", rng=random.Random(42))

    assert first == second
    assert first["roast_text"].startswith("Verdict:")
    assert "\nEvidence:\n- " in first["roast_text"]
    assert "\nBottom line: " in first["roast_text"]


def test_generate_roast_changes_with_different_seeds():
    first = generate_roast(copy.deepcopy(FINDINGS), SCORES, "brutal", rng=random.Random(1))
    second = generate_roast(copy.deepcopy(FINDINGS), SCORES, "brutal", rng=random.Random(2))

    assert first != second


def test_all_findings_negative_still_returns_strength_fallback():
    all_composite_findings = [
        {"metric": "fork_ratio", "detail": "too many forks", "value": 0.9, "contributes_to": "profile_strength"},
        {"metric": "repo_substance_score", "detail": "thin repos", "value": 0.2, "contributes_to": "project_depth"},
        {"metric": "generic_commit_ratio", "detail": "generic commits", "value": 0.8, "contributes_to": "commit_consistency"},
        {"metric": "tech_diversity_concentration", "detail": "one stack dominates", "value": 0.95, "contributes_to": "tech_diversity"},
    ]

    result = generate_roast(all_composite_findings, SCORES, "hell", rng=random.Random(7))

    assert result["strengths"]
    assert result["strengths"][0] == FALLBACK_STRENGTH


def test_roadmap_actions_trace_to_actual_finding_metrics():
    dataset = load_line_bank()
    result = generate_roast(copy.deepcopy(FINDINGS), SCORES, "medium", rng=random.Random(9))
    action_to_metric = {
        action: metric
        for metric, actions in dataset["roadmap_actions"].items()
        for action in actions
    }
    finding_metrics = {finding["metric"] for finding in FINDINGS}

    for week in result["roadmap"]:
        assert week["actions"]
        for action in week["actions"]:
            assert action_to_metric[action] in finding_metrics


def test_improvement_areas_are_action_oriented():
    dataset = load_line_bank()
    result = generate_roast(copy.deepcopy(FINDINGS), SCORES, "medium", rng=random.Random(11))
    actions = {
        action
        for actions in dataset["roadmap_actions"].values()
        for action in actions
    }

    assert result["improvement_areas"]
    assert all(any(action in item for action in actions) for item in result["improvement_areas"])
