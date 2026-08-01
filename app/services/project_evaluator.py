from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.models.api import (
    ProjectCategoryEvaluation,
    ProjectEvaluationFlags,
    ProjectEvaluationResponse,
    ProjectEvidencePoint,
    ProjectType,
)


PROJECT_EVALUATOR_SCHEMA_VERSION = 2
CALIBRATION_NOTE = (
    "This is a deterministic, evidence-limited review rather than a population-calibrated benchmark. "
    "Use the cited repository evidence alongside the score."
)
CATEGORY_WEIGHTS = {
    "problem_statement_alignment": 25,
    "code_quality": 20,
    "security": 15,
    "testing_reliability": 15,
    "efficiency": 15,
    "documentation_accessibility": 10,
}
COMMON_WORDS = {
    "about",
    "after",
    "against",
    "build",
    "from",
    "have",
    "into",
    "project",
    "should",
    "that",
    "their",
    "this",
    "user",
    "users",
    "with",
    "would",
}
SOURCE_SUFFIXES = (".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".rb", ".php", ".cs")
UI_PROJECT_TYPES = {"web_app"}


def evaluate_project(problem_statement: str, evidence_bundle: dict[str, Any]) -> ProjectEvaluationResponse:
    files = list(evidence_bundle.get("files") or [])
    tree_files = list(evidence_bundle.get("tree_files") or [])
    static_signals = compute_static_signals(files, tree_files)
    project_type = detect_project_type(files, tree_files)
    # Documentation and accessibility are currently one combined axis. Until
    # they are modelled separately, exclude the actual category for projects
    # where the accessibility half is not applicable rather than presenting a
    # misleading exclusion that leaves the category in the composite.
    excluded = [] if project_type in UI_PROJECT_TYPES else ["documentation_accessibility"]
    flags = ProjectEvaluationFlags(
        possible_stub_implementation=static_signals["possible_stub_implementation"],
        insufficient_evidence_gathered=len(files) < 5,
    )

    categories = {
        "problem_statement_alignment": score_problem_alignment(problem_statement, files, static_signals, flags),
        "code_quality": score_code_quality(files, static_signals, flags),
        "security": score_security(files, static_signals, flags),
        "testing_reliability": score_testing(static_signals),
        "efficiency": score_efficiency(files, static_signals),
        "documentation_accessibility": score_docs_accessibility(project_type, files, static_signals),
    }
    categories = {
        key: category
        for key, category in categories.items()
        if key not in excluded
    }
    categories = adversarial_self_check(categories, flags)
    overall = weighted_average(categories)
    return ProjectEvaluationResponse(
        project_type=project_type,
        excluded_categories=excluded,
        categories=categories,
        overall_score=overall,
        grade_label=grade_label(overall),
        calibration_note=CALIBRATION_NOTE,
        flags=flags,
    )


def compute_static_signals(files: list[dict[str, Any]], tree_files: list[dict[str, Any]]) -> dict[str, Any]:
    paths = [str(entry.get("path") or "") for entry in tree_files]
    fetched_paths = [str(file.get("path") or "") for file in files]
    source_paths = [path for path in paths if is_source_file(path) and not is_test_file(path)]
    test_paths = [path for path in paths if is_test_file(path)]
    manifest_paths = [path for path in paths if is_manifest(path)]
    workflow_paths = [path for path in paths if path.lower().startswith(".github/workflows/")]
    lint_config_paths = [path for path in paths if is_lint_config(path)]
    line_counts = {
        str(file.get("path") or ""): len(str(file.get("text") or "").splitlines())
        for file in files
    }
    source_line_counts = {path: count for path, count in line_counts.items() if is_source_file(path)}
    text_by_path = {str(file.get("path") or ""): str(file.get("text") or "") for file in files}
    readme = first_readme(files)
    vulnerable = known_vulnerable_dependency_findings(files)

    return {
        "source_file_count": len(source_paths),
        "test_file_count": len(test_paths),
        "test_to_source_ratio": round(len(test_paths) / max(len(source_paths), 1), 3),
        "ci_present": bool(workflow_paths),
        "workflow_paths": workflow_paths,
        "lint_config_present": bool(lint_config_paths),
        "lint_config_paths": lint_config_paths,
        "manifest_paths": manifest_paths,
        "fetched_paths": fetched_paths,
        "readme_path": str(readme.get("path") or "") if readme else "",
        "readme_text": str(readme.get("text") or "") if readme else "",
        "loc_outliers": [path for path, count in source_line_counts.items() if count > 400],
        "known_vulnerable_dependency_findings": vulnerable,
        "uses_env_config": any(re.search(r"\b(process\.env|os\.environ|getenv|BaseSettings|import\.meta\.env)\b", text) for text in text_by_path.values()),
        "input_validation_markers": any(re.search(r"\b(pydantic|zod|joi|validator|Field\(|body\(|query\(|params\()", text, re.I) for text in text_by_path.values()),
        "auth_markers": any(re.search(r"\b(auth|jwt|oauth|session|permission|authorize|basic)\b", text, re.I) for text in text_by_path.values()),
        "abuse_protection_markers": any(re.search(r"\b(rate.?limit|throttle|captcha|retry-after|fixedwindow)\b", text, re.I) for text in text_by_path.values()),
        "secret_findings": hardcoded_secret_findings(files),
        "possible_stub_implementation": possible_stub_implementation(text_by_path),
        "cache_markers": any(re.search(r"\b(cache|memoize|revalidate|ttl|etag)\b", text, re.I) for text in text_by_path.values()),
        "pagination_batch_markers": any(re.search(r"\b(pagination|page_size|cursor|batch|limit|offset|first:|after:)\b", text, re.I) for text in text_by_path.values()),
        "async_markers": any(re.search(r"\b(async|await|Promise\.all|TaskGroup|gather)\b", text) for text in text_by_path.values()),
        "retry_backoff_markers": any(re.search(r"\b(backoff|retry|Retry-After|exponential)\b", text, re.I) for text in text_by_path.values()),
        "semantic_ui_markers": any(re.search(r"\b(aria-|<label|htmlFor=|<main|<nav|alt=|role=)\b", text) for text in text_by_path.values()),
    }


def detect_project_type(files: list[dict[str, Any]], tree_files: list[dict[str, Any]]) -> ProjectType:
    paths = {str(entry.get("path") or "").lower() for entry in tree_files}
    fetched = "\n".join(str(file.get("text") or "")[:4000].lower() for file in files)
    if {"next.config.js", "next.config.mjs", "vite.config.ts", "vite.config.js"} & {path.rsplit("/", 1)[-1] for path in paths}:
        return "web_app"
    if "package.json" in {path.rsplit("/", 1)[-1] for path in paths} and any(path.endswith((".tsx", ".jsx")) for path in paths):
        return "web_app"
    if "console_scripts" in fetched or any(path.startswith(("cli/", "cmd/")) for path in paths):
        return "cli_tool"
    if any(path.endswith(".ipynb") for path in paths) or any("notebook" in path for path in paths):
        return "data_science"
    if "fastapi" in fetched or "flask" in fetched or "express" in fetched or any(path.endswith(("server.py", "app.py", "main.py")) for path in paths):
        return "api_backend"
    if any(path.endswith(("pyproject.toml", "cargo.toml", "go.mod")) for path in paths):
        return "library"
    return "other"


def score_problem_alignment(
    problem_statement: str,
    files: list[dict[str, Any]],
    static_signals: dict[str, Any],
    flags: ProjectEvaluationFlags,
) -> ProjectCategoryEvaluation:
    terms = important_terms(problem_statement)
    source_hits = term_hits(terms, files, source_only=True)
    all_hits = term_hits(terms, files, source_only=False)
    evidence = [
        ProjectEvidencePoint(file=item["file"], detail=item["detail"])
        for item in source_hits[:3] or all_hits[:3]
    ]
    if not evidence:
        evidence.append(ProjectEvidencePoint(file="repository tree", detail="No retrieved code file contained distinctive terms from the submitted problem statement."))

    score = 20
    band = "0-20: the retrieved evidence does not show implementation of the stated problem."
    if len(source_hits) >= 3 and static_signals["source_file_count"] >= 3:
        score = 68
        band = "61-80: source files address the main stated concepts, though this deterministic pass cannot prove every edge case."
    elif len(source_hits) >= 1:
        score = 52
        band = "41-60: core concepts appear in implementation files, but evidence is thin or incomplete."
    elif len(all_hits) >= 2:
        score = 34
        band = "21-40: project claims line up in docs/config more than in retrieved implementation."
        flags.claims_exceed_evidence = True

    if static_signals["possible_stub_implementation"]:
        score = min(score, 55)
        flags.possible_stub_implementation = True
        band += " Stub/mock/placeholder markers cap the score in the 41-60 band until the core behavior is verified."
    return ProjectCategoryEvaluation(score=score, band_justification=band, evidence=evidence[:4])


def score_code_quality(
    files: list[dict[str, Any]],
    static_signals: dict[str, Any],
    flags: ProjectEvaluationFlags,
) -> ProjectCategoryEvaluation:
    evidence = [
        ProjectEvidencePoint(file="repository tree", detail=f"{static_signals['source_file_count']} source files were detected outside tests."),
    ]
    if static_signals["lint_config_present"]:
        evidence.append(ProjectEvidencePoint(file=static_signals["lint_config_paths"][0], detail="A lint/type-quality configuration file is present."))
    if static_signals["loc_outliers"]:
        evidence.append(ProjectEvidencePoint(file=static_signals["loc_outliers"][0], detail="This source file exceeds 400 lines, which is a maintainability outlier."))
    if any_error_handling(files):
        evidence.append(ProjectEvidencePoint(file=first_matching_file(files, r"\b(try:|except |catch \(|raise |throw new)\b"), detail="Retrieved source includes explicit error handling paths."))

    score = 45
    band = "41-60: reasonable structure is visible, but the retrieved sample does not prove senior-review-level design."
    if static_signals["source_file_count"] <= 1:
        score = 28
        band = "21-40: the repository exposes very little source structure in the fetched evidence."
    elif static_signals["lint_config_present"] and any_error_handling(files) and not static_signals["loc_outliers"]:
        score = 72
        band = "61-80: structure, style tooling, and important-path error handling are visible in code."
    if static_signals["possible_stub_implementation"]:
        score = min(score, 58)
        flags.possible_stub_implementation = True
        band += " Stub/mock markers prevent a higher code-quality score."
    return ProjectCategoryEvaluation(score=score, band_justification=band, evidence=evidence[:4])


def score_security(
    files: list[dict[str, Any]],
    static_signals: dict[str, Any],
    flags: ProjectEvaluationFlags,
) -> ProjectCategoryEvaluation:
    if static_signals["secret_findings"]:
        finding = static_signals["secret_findings"][0]
        return ProjectCategoryEvaluation(
            score=12,
            band_justification="0-20: retrieved evidence includes a hardcoded secret-like value.",
            evidence=[ProjectEvidencePoint(file=finding["file"], detail=finding["detail"])],
        )

    evidence = []
    if static_signals["uses_env_config"]:
        evidence.append(ProjectEvidencePoint(file=first_matching_file(files, r"\b(process\.env|os\.environ|getenv|BaseSettings|import\.meta\.env)\b"), detail="Configuration is read from environment variables rather than obvious literals."))
    if static_signals["input_validation_markers"]:
        evidence.append(ProjectEvidencePoint(file=first_matching_file(files, r"\b(pydantic|zod|joi|validator|Field\(|body\(|query\(|params\()", re.I), detail="Input validation markers are present in retrieved code."))
    if static_signals["abuse_protection_markers"]:
        evidence.append(ProjectEvidencePoint(file=first_matching_file(files, r"\b(rate.?limit|throttle|captcha|retry-after|fixedwindow)\b", re.I), detail="Abuse-protection or rate-limit logic appears in code."))
    if static_signals["known_vulnerable_dependency_findings"]:
        dep = static_signals["known_vulnerable_dependency_findings"][0]
        evidence.append(ProjectEvidencePoint(file=dep["file"], detail=dep["detail"]))

    score = 34
    band = "21-40: no committed secret was found, but the fetched evidence does not show a complete public-input security posture."
    if static_signals["known_vulnerable_dependency_findings"]:
        score = 28
        band = "21-40: known-vulnerable dependency ranges were detected in manifests."
    elif static_signals["uses_env_config"] and static_signals["input_validation_markers"] and static_signals["abuse_protection_markers"]:
        score = 74
        band = "61-80: env-based secrets, validation, and an abuse-protection layer are visible."
    elif static_signals["uses_env_config"] and static_signals["input_validation_markers"]:
        score = 56
        band = "41-60: basic validation and environment-based config are visible, but abuse protection is thin."
    if not evidence:
        evidence.append(ProjectEvidencePoint(file="retrieved files", detail="No secret-like literals were found, but no positive validation/auth evidence was retrieved either."))
        flags.insufficient_evidence_gathered = True
    return ProjectCategoryEvaluation(score=score, band_justification=band, evidence=evidence[:4])


def score_testing(static_signals: dict[str, Any]) -> ProjectCategoryEvaluation:
    test_count = static_signals["test_file_count"]
    ratio = static_signals["test_to_source_ratio"]
    evidence = [
        ProjectEvidencePoint(file="repository tree", detail=f"{test_count} test files for {static_signals['source_file_count']} source files; ratio {ratio}.")
    ]
    if static_signals["ci_present"]:
        evidence.append(ProjectEvidencePoint(file=static_signals["workflow_paths"][0], detail="A GitHub Actions workflow is present."))

    if test_count == 0:
        score = 12
        band = "0-20: no tests exist anywhere in the repository tree."
    elif ratio < 0.08:
        score = 34
        band = "21-40: tests exist, but the test-to-source ratio is very thin."
    elif static_signals["ci_present"] and ratio >= 0.2:
        score = 74
        band = "61-80: meaningful test volume is visible and tests appear to run in CI."
    else:
        score = 52
        band = "41-60: tests cover some project logic, but CI or edge-case confidence is incomplete."
    return ProjectCategoryEvaluation(score=score, band_justification=band, evidence=evidence)


def score_efficiency(files: list[dict[str, Any]], static_signals: dict[str, Any]) -> ProjectCategoryEvaluation:
    evidence = []
    if static_signals["pagination_batch_markers"]:
        evidence.append(ProjectEvidencePoint(file=first_matching_file(files, r"\b(pagination|page_size|cursor|batch|limit|offset|first:|after:)\b", re.I), detail="Retrieved code contains pagination, batching, or explicit limit markers."))
    if static_signals["cache_markers"]:
        evidence.append(ProjectEvidencePoint(file=first_matching_file(files, r"\b(cache|memoize|revalidate|ttl|etag)\b", re.I), detail="Retrieved code contains caching or freshness-control markers."))
    if static_signals["retry_backoff_markers"]:
        evidence.append(ProjectEvidencePoint(file=first_matching_file(files, r"\b(backoff|retry|Retry-After|exponential)\b", re.I), detail="Retry/backoff handling appears in retrieved code."))
    if static_signals["async_markers"]:
        evidence.append(ProjectEvidencePoint(file=first_matching_file(files, r"\b(async|await|Promise\.all|TaskGroup|gather)\b"), detail="Async execution markers are present in retrieved source."))

    if static_signals["pagination_batch_markers"] and static_signals["cache_markers"] and static_signals["retry_backoff_markers"]:
        score = 84
        band = "81-100: bounded external/API work, caching, and retry/backoff behavior are visible in code."
    elif static_signals["pagination_batch_markers"] and (static_signals["cache_markers"] or static_signals["async_markers"]):
        score = 72
        band = "61-80: reasonable bounding and async/cache behavior appear where scale may matter."
    elif evidence:
        score = 52
        band = "41-60: some bounding or async behavior appears, but scale protections are inconsistent."
    else:
        score = 32
        band = "21-40: no caching, pagination, batching, or retry/backoff evidence was retrieved."
        evidence.append(ProjectEvidencePoint(file="retrieved files", detail="The fetched sample did not contain scale-control markers."))
    return ProjectCategoryEvaluation(score=score, band_justification=band, evidence=evidence[:4])


def score_docs_accessibility(
    project_type: ProjectType,
    files: list[dict[str, Any]],
    static_signals: dict[str, Any],
) -> ProjectCategoryEvaluation:
    readme_path = static_signals["readme_path"] or "repository tree"
    readme_text = static_signals["readme_text"]
    evidence = []
    if readme_text:
        evidence.append(ProjectEvidencePoint(file=readme_path, detail="README was retrieved for setup/onboarding review."))
    else:
        evidence.append(ProjectEvidencePoint(file="repository tree", detail="No README file was retrieved."))

    has_install = bool(re.search(r"\b(install|setup|npm install|pip install|poetry install|cargo build)\b", readme_text, re.I))
    has_usage = bool(re.search(r"\b(usage|run|start|example|curl|npm run|python )\b", readme_text, re.I))
    has_config = bool(re.search(r"\b(env|configuration|config|secret|token|api key)\b", readme_text, re.I))
    has_limits = bool(re.search(r"\b(limitations|troubleshooting|known issue|scope)\b", readme_text, re.I))
    if project_type in UI_PROJECT_TYPES and static_signals["semantic_ui_markers"]:
        evidence.append(ProjectEvidencePoint(file=first_matching_file(files, r"\b(aria-|<label|htmlFor=|<main|<nav|alt=|role=)\b"), detail="Semantic or accessibility-oriented UI markers are present."))

    if not readme_text:
        score = 12
        band = "0-20: no README was available in the retrieved repository evidence."
    elif has_install and has_usage and has_config and has_limits and (project_type not in UI_PROJECT_TYPES or static_signals["semantic_ui_markers"]):
        score = 86
        band = "81-100: setup, usage, configuration, limitations/troubleshooting, and applicable UI accessibility basics are visible."
    elif has_install and has_usage and (project_type not in UI_PROJECT_TYPES or static_signals["semantic_ui_markers"]):
        score = 72
        band = "61-80: install/run guidance is present and applicable accessibility basics are visible when a UI exists."
    elif has_install or has_usage:
        score = 52
        band = "41-60: README has minimal onboarding, but architecture/configuration or accessibility evidence is thin."
    else:
        score = 28
        band = "21-40: README exists but does not provide working setup and usage guidance."
    return ProjectCategoryEvaluation(score=score, band_justification=band, evidence=evidence[:4])


def adversarial_self_check(
    categories: dict[str, ProjectCategoryEvaluation],
    flags: ProjectEvaluationFlags,
) -> dict[str, ProjectCategoryEvaluation]:
    checked = {}
    for key, category in categories.items():
        evidence = list(category.evidence)
        code_evidence_count = sum(1 for item in evidence if is_code_level_evidence(item.file))
        if category.score >= 80 and code_evidence_count < 2 and key != "documentation_accessibility":
            category = category.model_copy(
                update={
                    "score": 79,
                    "band_justification": (
                        f"{category.band_justification} Self-check capped this below 80 because it has fewer "
                        "than two independent code-level evidence citations."
                    ),
                }
            )
            flags.insufficient_evidence_gathered = True
        checked[key] = category
    return checked


def weighted_average(categories: dict[str, ProjectCategoryEvaluation]) -> float:
    total_weight = sum(CATEGORY_WEIGHTS[key] for key in categories)
    weighted = sum(categories[key].score * CATEGORY_WEIGHTS[key] for key in categories)
    return round(weighted / total_weight, 1)


def grade_label(score: float) -> str:
    if score >= 90:
        return "Exceptional, rare"
    if score >= 80:
        return "Strong, evidence-backed"
    if score >= 70:
        return "Solid, with real gaps"
    if score >= 55:
        return "Developing, usable but uneven"
    if score >= 40:
        return "Thin, major gaps"
    return "Weak, not yet defensible"


def important_terms(problem_statement: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{3,}", problem_statement.lower())
    counts = Counter(word for word in words if word not in COMMON_WORDS)
    return [word for word, _ in counts.most_common(12)]


def term_hits(terms: list[str], files: list[dict[str, Any]], *, source_only: bool) -> list[dict[str, str]]:
    hits = []
    for file in files:
        path = str(file.get("path") or "")
        if source_only and not is_source_file(path):
            continue
        text = str(file.get("text") or "").lower()
        matched = [term for term in terms if term in text]
        if matched:
            hits.append({"file": path, "detail": f"Contains problem-statement terms: {', '.join(matched[:5])}."})
    return hits


def first_readme(files: list[dict[str, Any]]) -> dict[str, Any] | None:
    for file in files:
        path = str(file.get("path") or "").lower().rsplit("/", 1)[-1]
        if path.startswith("readme"):
            return file
    return None


def possible_stub_implementation(text_by_path: dict[str, str]) -> bool:
    for path, text in text_by_path.items():
        if re.search(r"\b(todo|stub|placeholder|fake data|lorem ipsum)\b", text, re.I):
            return True
        if not is_test_file(path) and re.search(r"\bmock\b", text, re.I):
            return True
    return False


def first_matching_file(files: list[dict[str, Any]], pattern: str, flags: int = 0) -> str:
    for file in files:
        if re.search(pattern, str(file.get("text") or ""), flags):
            return str(file.get("path") or "retrieved files")
    return "retrieved files"


def any_error_handling(files: list[dict[str, Any]]) -> bool:
    return any(re.search(r"\b(try:|except |catch \(|raise |throw new)\b", str(file.get("text") or "")) for file in files)


def is_manifest(path: str) -> bool:
    name = path.lower().rsplit("/", 1)[-1]
    return name in {"package.json", "pyproject.toml", "requirements.txt", "poetry.lock", "cargo.toml", "go.mod"}


def is_lint_config(path: str) -> bool:
    name = path.lower().rsplit("/", 1)[-1]
    return name in {".eslintrc", ".eslintrc.json", "eslint.config.js", "ruff.toml", "mypy.ini", "tsconfig.json", "pyproject.toml"}


def is_source_file(path: str) -> bool:
    lowered = path.lower()
    if is_test_file(lowered) or lowered.endswith(".d.ts"):
        return False
    return lowered.endswith(SOURCE_SUFFIXES)


def is_test_file(path: str) -> bool:
    lowered = path.lower()
    name = lowered.rsplit("/", 1)[-1]
    return (
        "/test/" in lowered
        or "/tests/" in lowered
        or name.startswith("test_")
        or ".test." in name
        or ".spec." in name
    )


def is_code_level_evidence(path: str) -> bool:
    lowered = path.lower()
    if lowered in {"retrieved files", "repository tree"}:
        return False
    if lowered.rsplit("/", 1)[-1].startswith("readme"):
        return False
    return lowered.endswith(SOURCE_SUFFIXES + (".json", ".toml", ".yml", ".yaml"))


def known_vulnerable_dependency_findings(files: list[dict[str, Any]]) -> list[dict[str, str]]:
    findings = []
    vulnerable_patterns = [
        (r'"lodash"\s*:\s*"[\^~]?4\.(?:0|1[0-6])\.', "lodash below 4.17.21 is commonly flagged by audit tooling."),
        (r'"minimist"\s*:\s*"[\^~]?0\.', "minimist 0.x is commonly flagged by audit tooling."),
        (r'"axios"\s*:\s*"[\^~]?0\.', "axios 0.x is commonly flagged by audit tooling."),
        (r"django\s*==\s*2\.", "Django 2.x is end-of-life and should not be used for new public apps."),
        (r"flask\s*==\s*0\.", "Flask 0.x is obsolete and should be upgraded."),
    ]
    for file in files:
        path = str(file.get("path") or "")
        if not is_manifest(path):
            continue
        text = str(file.get("text") or "").lower()
        for pattern, detail in vulnerable_patterns:
            if re.search(pattern, text, re.I):
                findings.append({"file": path, "detail": detail})
    return findings


def hardcoded_secret_findings(files: list[dict[str, Any]]) -> list[dict[str, str]]:
    findings = []
    secret_patterns = [
        (r"gh[pousr]_[A-Za-z0-9_]{20,}", "A GitHub token-like literal appears in retrieved content."),
        (r"sk-[A-Za-z0-9]{24,}", "An OpenAI-style API key literal appears in retrieved content."),
        (r"AKIA[0-9A-Z]{16}", "An AWS access-key-like literal appears in retrieved content."),
        (r"(?i)(api[_-]?key|secret|password)\s*=\s*['\"][^'\"]{16,}['\"]", "A secret-like assignment appears in retrieved content."),
    ]
    for file in files:
        path = str(file.get("path") or "")
        text = str(file.get("text") or "")
        for pattern, detail in secret_patterns:
            if re.search(pattern, text):
                findings.append({"file": path, "detail": detail})
    return findings
