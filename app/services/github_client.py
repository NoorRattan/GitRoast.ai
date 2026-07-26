import asyncio
from dataclasses import dataclass
from typing import Any

import httpx


GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"


class GitHubClientError(Exception):
    def __init__(self, message: str, status_code: int | None = None, retryable: bool = False) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class GitHubRateLimitError(GitHubClientError):
    pass


@dataclass(frozen=True)
class GitHubProfileRequest:
    username: str
    max_repos: int = 50
    language_limit: int = 10


PROFILE_QUERY = """
query GitRoastProfile($login: String!, $maxRepos: Int!, $languageLimit: Int!) {
  user(login: $login) {
    login
    createdAt
    avatarUrl
    pullRequests(first: 1) {
      totalCount
    }
    repositories(
      first: $maxRepos
      ownerAffiliations: OWNER
      orderBy: {field: PUSHED_AT, direction: DESC}
    ) {
      nodes {
        name
        isFork
        isPrivate
        diskUsage
        pushedAt
        stargazerCount
        isArchived
        licenseInfo {
          key
        }
        languages(first: $languageLimit, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node {
              name
            }
          }
        }
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 20) {
                totalCount
                nodes {
                  committedDate
                  messageHeadline
                }
              }
            }
          }
        }
        rootTree: object(expression: "HEAD:") {
          ... on Tree {
            entries {
              name
              type
            }
          }
        }
      }
    }
  }
}
"""


class GitHubGraphQLClient:
    def __init__(
        self,
        token: str,
        http_client: httpx.AsyncClient,
        *,
        max_repos: int = 50,
        sleep=asyncio.sleep,
    ) -> None:
        self._token = token
        self._http_client = http_client
        self._max_repos = max_repos
        self._sleep = sleep
        self._semaphore = asyncio.Semaphore(1)

    async def query_user_profile(self, username: str, *, max_repos: int | None = None) -> dict[str, Any]:
        request = GitHubProfileRequest(username=username, max_repos=max_repos or self._max_repos)
        payload = await self.execute(
            PROFILE_QUERY,
            {
                "login": request.username,
                "maxRepos": request.max_repos,
                "languageLimit": request.language_limit,
            },
        )
        return parse_profile_response(payload, max_repos=request.max_repos)

    async def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        async with self._semaphore:
            return await self._execute_serialized(query, variables or {})

    async def _execute_serialized(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        undocumented_failures = 0
        while True:
            response = await self._http_client.post(
                GITHUB_GRAPHQL_URL,
                json={"query": query, "variables": variables},
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/vnd.github+json",
                },
            )

            if response.status_code in {403, 429}:
                retry_after = response.headers.get("Retry-After")
                if retry_after is not None:
                    await self._sleep(int(retry_after))
                    continue

                undocumented_failures += 1
                if undocumented_failures >= 3:
                    raise GitHubRateLimitError(
                        "GitHub secondary rate limit did not include Retry-After",
                        status_code=response.status_code,
                        retryable=True,
                    )
                await self._sleep(min(2 ** (undocumented_failures - 1), 8))
                continue

            if response.status_code >= 400:
                raise GitHubClientError(
                    f"GitHub GraphQL request failed with status {response.status_code}",
                    status_code=response.status_code,
                    retryable=response.status_code >= 500,
                )

            payload = response.json()
            if payload.get("errors"):
                raise GitHubClientError(str(payload["errors"]), status_code=response.status_code)
            return payload


def parse_profile_response(payload: dict[str, Any], *, max_repos: int | None = None) -> dict[str, Any]:
    data = payload.get("data", payload)
    user = data.get("user")
    if user is None:
        raise GitHubClientError("GitHub user not found", status_code=404)

    raw_repos = user.get("repositories", {}).get("nodes", []) or []
    repos = [_parse_repo(repo) for repo in raw_repos]
    repos.sort(key=lambda repo: repo.get("pushed_at") or "", reverse=True)
    if max_repos is not None:
        repos = repos[:max_repos]

    return {
        "username": user.get("login"),
        "created_at": user.get("createdAt"),
        "avatar_url": user.get("avatarUrl"),
        "external_pr_count": user.get("external_pr_count", user.get("pullRequests", {}).get("totalCount", 0)),
        "repos": repos,
    }


def _parse_repo(repo: dict[str, Any]) -> dict[str, Any]:
    branch_target = ((repo.get("defaultBranchRef") or {}).get("target") or {})
    history = branch_target.get("history") or {}
    commit_nodes = history.get("nodes") or []
    root_tree = repo.get("rootTree") or repo.get("object") or {}
    entries = root_tree.get("entries") or []

    return {
        "name": repo.get("name"),
        "is_fork": bool(repo.get("isFork")),
        "is_private": bool(repo.get("isPrivate")),
        "is_archived": bool(repo.get("isArchived")),
        "disk_usage": int(repo.get("diskUsage") or 0),
        "pushed_at": repo.get("pushedAt"),
        "stargazer_count": int(repo.get("stargazerCount") or 0),
        "is_pinned": bool(repo.get("isPinned", repo.get("is_pinned", False))),
        "has_license": bool(repo.get("licenseInfo") or repo.get("has_license")),
        "languages": {
            edge.get("node", {}).get("name"): int(edge.get("size") or 0)
            for edge in (repo.get("languages", {}).get("edges") or [])
            if edge.get("node", {}).get("name")
        },
        "commit_count": int(history.get("totalCount") or repo.get("commit_count") or 0),
        "commit_messages": [
            node.get("messageHeadline") or node.get("message") or ""
            for node in commit_nodes
        ]
        or list(repo.get("commit_messages", [])),
        "commit_dates": [
            node.get("committedDate") or node.get("date")
            for node in commit_nodes
            if node.get("committedDate") or node.get("date")
        ]
        or list(repo.get("commit_dates", [])),
        "root_entries": [{"name": entry.get("name"), "type": entry.get("type")} for entry in entries],
        "readme_text": repo.get("readme_text", ""),
        "has_coverage_badge": bool(repo.get("has_coverage_badge", False)),
    }
