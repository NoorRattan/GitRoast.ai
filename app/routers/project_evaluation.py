import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core.errors import APIError
from app.dependencies import cache_client_dependency, github_client_dependency, rate_limiters_dependency
from app.models.api import ProjectEvaluationRequest
from app.services import cache
from app.services.github_client import GitHubClientError, GitHubGraphQLClient
from app.services.project_evaluator import PROJECT_EVALUATOR_SCHEMA_VERSION, evaluate_project
from app.services.rate_limit import RateLimiterRegistry


router = APIRouter(prefix="/api/v1")
_evaluation_locks: dict[str, asyncio.Lock] = {}


@router.post("/project-evaluation")
async def post_project_evaluation(
    payload: ProjectEvaluationRequest,
    request: Request,
    cache_client=Depends(cache_client_dependency),
    github_client: GitHubGraphQLClient = Depends(github_client_dependency),
    rate_limiters: RateLimiterRegistry = Depends(rate_limiters_dependency),
) -> dict[str, Any]:
    await rate_limiters.check("project_evaluation", request)
    try:
        await rate_limiters.check_global("github_capacity", request)
        revision = await github_client.query_repository_revision(payload.repo_url)
    except GitHubClientError as exc:
        if exc.status_code == 404:
            raise APIError(404, "not_found", "GitHub repository not found.") from exc
        if exc.status_code == 422:
            raise APIError(422, "validation_error", "Enter a valid public GitHub repository URL.") from exc
        raise APIError(503, "github_unavailable", "GitHub is temporarily unavailable.") from exc

    cached = await cache.get_project_evaluation(
        cache_client,
        revision["repo_url"],
        revision["commit_sha"],
        payload.problem_statement,
        PROJECT_EVALUATOR_SCHEMA_VERSION,
    )
    if cached is not None:
        cached.pop("cached_at", None)
        return cached

    lock_key = f"{revision['repo_url']}:{revision['commit_sha']}:{payload.problem_statement}"
    lock = _evaluation_locks.setdefault(lock_key, asyncio.Lock())
    try:
        async with lock:
            cached = await cache.get_project_evaluation(
                cache_client,
                revision["repo_url"],
                revision["commit_sha"],
                payload.problem_statement,
                PROJECT_EVALUATOR_SCHEMA_VERSION,
            )
            if cached is not None:
                cached.pop("cached_at", None)
                return cached
            try:
                evidence_bundle = await github_client.query_repository_evidence_for_revision(revision)
            except GitHubClientError as exc:
                if exc.status_code == 404:
                    raise APIError(404, "not_found", "GitHub repository not found.") from exc
                raise APIError(503, "github_unavailable", "GitHub is temporarily unavailable.") from exc
            evaluation = evaluate_project(payload.problem_statement, evidence_bundle)
            response = evaluation.model_dump(mode="json")
            await cache.set_project_evaluation(
                cache_client,
                revision["repo_url"],
                revision["commit_sha"],
                payload.problem_statement,
                PROJECT_EVALUATOR_SCHEMA_VERSION,
                response,
            )
            return response
    finally:
        if not lock.locked():
            _evaluation_locks.pop(lock_key, None)
