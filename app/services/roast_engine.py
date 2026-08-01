import json
import random
import re
from pathlib import Path
from string import Formatter
from typing import Any

from app.services.scoring_constants import COMPOSITE_SCORE_KEYS, FindingMetric


INTENSITIES = ("mild", "medium", "brutal", "hell")
SUPPORTED_PLACEHOLDERS = frozenset(
    {"detail", "ratio_pct", "value_pct", "metric_label", "composite_label", "score"}
)
MIN_FINDING_TEMPLATES_PER_BUCKET = 8
FALLBACK_STRENGTH = "There is enough public work here to improve quickly once the weakest signals are cleaned up."

DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "roast_lines.json"

METRIC_TO_COMPOSITE = {
    FindingMetric.graveyard_ratio.value: "project_depth",
    FindingMetric.generic_commit_ratio.value: "commit_consistency",
    FindingMetric.active_weeks_ratio.value: "commit_consistency",
    FindingMetric.fork_ratio.value: "profile_strength",
    FindingMetric.license_coverage.value: "profile_strength",
    FindingMetric.pinned_curation_mismatch.value: "profile_strength",
    FindingMetric.readme_heuristic_gaps.value: "profile_strength",
    FindingMetric.tech_diversity_concentration.value: "tech_diversity",
    FindingMetric.repo_substance_score.value: "project_depth",
    FindingMetric.ci_hygiene_gap.value: "project_depth",
}

COMPOSITE_TO_METRICS = {
    composite: [metric for metric, mapped in METRIC_TO_COMPOSITE.items() if mapped == composite]
    for composite in COMPOSITE_SCORE_KEYS
}
COMPOSITE_TO_METRICS = {composite: metrics for composite, metrics in COMPOSITE_TO_METRICS.items() if metrics}


class RoastDatasetError(ValueError):
    pass


def generate_roast(
    findings: list[dict[str, Any]],
    scores: dict[str, int],
    intensity_applied: str,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    rng = rng or random.Random()
    dataset = load_line_bank()
    if intensity_applied not in INTENSITIES:
        raise ValueError(f"unsupported roast intensity: {intensity_applied}")

    ordered_findings = list(findings)
    opener = rng.choice(dataset["openers"][intensity_applied])
    closer = rng.choice(dataset["closers"][intensity_applied])
    evidence_findings = ordered_findings[:6]
    evidence_lines = [
        _fill_template(
            rng.choice(dataset["finding_lines"][finding["metric"]][intensity_applied]),
            finding,
            scores,
        )
        for finding in evidence_findings
    ]
    if len(ordered_findings) > len(evidence_findings):
        evidence_lines.append(f"{len(ordered_findings) - len(evidence_findings)} more lower-priority signals are also dragging the audit down.")

    improvement_areas = _improvement_areas(dataset, ordered_findings, rng)
    strengths = _strengths(dataset, ordered_findings, scores, rng)
    roadmap = _roadmap(dataset, ordered_findings, rng)

    return {
        "roast_text": _compose_roast_text(opener, evidence_lines, closer),
        "strengths": strengths,
        "improvement_areas": improvement_areas,
        "roadmap": roadmap,
    }


def should_queue_for_review(findings: list[dict[str, Any]]) -> bool:
    return len(findings) < 6


def _compose_roast_text(opener: str, evidence_lines: list[str], closer: str) -> str:
    if not evidence_lines:
        return f"Verdict: {opener}\n\nBottom line: {closer}"

    bullets = "\n".join(f"- {line}" for line in evidence_lines)
    return f"Verdict: {opener}\n\nEvidence:\n{bullets}\n\nBottom line: {closer}"


def _improvement_areas(dataset: dict[str, Any], findings: list[dict[str, Any]], rng: random.Random) -> list[str]:
    improvements: list[str] = []
    for finding in findings[:5]:
        action = rng.choice(dataset["roadmap_actions"][finding["metric"]])
        candidate = f"{_label(finding['metric']).capitalize()}: {action}"
        if candidate not in improvements:
            improvements.append(candidate)
    if not improvements:
        improvements.append("Project depth: Deepen the two strongest repos before starting new ones.")
    return improvements


def load_line_bank() -> dict[str, Any]:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    validate_line_bank(dataset)
    return dataset


def validate_line_bank(dataset: dict[str, Any]) -> None:
    expected_metrics = {metric.value for metric in FindingMetric}
    if set(dataset.get("finding_lines", {})) != expected_metrics:
        raise RoastDatasetError("finding_lines must match the closed finding metric enum")
    for metric in expected_metrics:
        tiers = dataset["finding_lines"][metric]
        if set(tiers) != set(INTENSITIES):
            raise RoastDatasetError(f"{metric} must include all intensity tiers")
        for intensity, templates in tiers.items():
            _require_template_list(
                templates,
                f"finding_lines.{metric}.{intensity}",
                minimum=MIN_FINDING_TEMPLATES_PER_BUCKET,
            )

    for section in ("openers", "closers"):
        if set(dataset.get(section, {})) != set(INTENSITIES):
            raise RoastDatasetError(f"{section} must include all intensity tiers")
        for intensity, templates in dataset[section].items():
            _require_template_list(templates, f"{section}.{intensity}", minimum=4)

    for section in ("strength_lines", "roadmap_actions"):
        if set(dataset.get(section, {})) != expected_metrics:
            raise RoastDatasetError(f"{section} must match the closed finding metric enum")
        for metric, templates in dataset[section].items():
            _require_template_list(templates, f"{section}.{metric}", minimum=4)


def _strengths(
    dataset: dict[str, Any],
    findings: list[dict[str, Any]],
    scores: dict[str, int],
    rng: random.Random,
) -> list[str]:
    finding_composites = {finding["contributes_to"] for finding in findings}
    strong_composites = [
        composite
        for composite, score in scores.items()
        if composite in COMPOSITE_TO_METRICS and score >= 70 and composite not in finding_composites
    ]
    strengths = []
    for composite in strong_composites:
        metric = rng.choice(COMPOSITE_TO_METRICS[composite])
        strengths.append(rng.choice(dataset["strength_lines"][metric]))
        if len(strengths) >= 5:
            break
    if not strengths:
        strengths.append(FALLBACK_STRENGTH)
    while len(strengths) < 3:
        metric = rng.choice(list(METRIC_TO_COMPOSITE))
        candidate = rng.choice(dataset["strength_lines"][metric])
        if candidate not in strengths:
            strengths.append(candidate)
    return strengths[:5]


def _roadmap(dataset: dict[str, Any], findings: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    selected = list(findings[:4])
    if not selected:
        selected = [
            {"metric": "repo_substance_score", "contributes_to": "project_depth"},
            {"metric": "readme_heuristic_gaps", "contributes_to": "profile_strength"},
        ]
    while len(selected) < 2:
        selected.append(selected[0])
    weeks = []
    for week_number, finding in enumerate(selected[:4], start=1):
        action_pool = dataset["roadmap_actions"][finding["metric"]]
        weeks.append(
            {
                "week": week_number,
                "focus": _label(finding["contributes_to"]),
                "actions": rng.sample(action_pool, k=min(2, len(action_pool))),
            }
        )
    return weeks[: max(2, min(4, len(weeks)))]


def _fill_template(template: str, finding: dict[str, Any], scores: dict[str, int]) -> str:
    value = float(finding.get("value", 0.0))
    metric = str(finding.get("metric", ""))
    composite = str(finding.get("contributes_to", ""))
    placeholders = {
        "detail": str(finding.get("detail", "")),
        "ratio_pct": _format_pct(value),
        "value_pct": _format_pct(value),
        "metric_label": _label(metric),
        "composite_label": _label(composite),
        "score": str(scores.get(composite, "")),
    }
    return template.format(**placeholders)


def _require_template_list(templates: Any, path: str, *, minimum: int) -> None:
    if not isinstance(templates, list) or len(templates) < minimum:
        raise RoastDatasetError(f"{path} must contain at least {minimum} templates")
    for template in templates:
        if not isinstance(template, str) or not template.strip():
            raise RoastDatasetError(f"{path} contains an empty or non-string template")
        placeholders = {
            field_name
            for _, field_name, _, _ in Formatter().parse(template)
            if field_name is not None
        }
        unknown = placeholders - SUPPORTED_PLACEHOLDERS
        if unknown:
            raise RoastDatasetError(f"{path} contains unsupported placeholders: {sorted(unknown)}")


def _format_pct(value: float) -> str:
    return f"{round(value * 100)}%"


def _label(value: str) -> str:
    return re.sub(r"_+", " ", value).strip()
