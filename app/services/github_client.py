import asyncio
import base64
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx


GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
GITHUB_REST_URL = "https://api.github.com"
MAX_EVALUATION_FILES = 28
MAX_EVALUATION_FILE_BYTES = 40_000


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
    repo_page_size: int = 20
    language_limit: int = 10
    readme_limit: int = 12


PROFILE_QUERY = """
query GitRoastProfile($login: String!, $repoPageSize: Int!, $after: String, $languageLimit: Int!) {
  user(login: $login) {
    login
    createdAt
    avatarUrl
    pullRequests(first: 1) {
      totalCount
    }
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
        }
      }
    }
    repositories(
      first: $repoPageSize
      after: $after
      ownerAffiliations: OWNER
      orderBy: {field: PUSHED_AT, direction: DESC}
    ) {
      pageInfo {
        hasNextPage
        endCursor
      }
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
              oldestHistory: history(last: 1) {
                nodes {
                  committedDate
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

README_QUERY = """
query GitRoastReadme($login: String!, $repo: String!, $expression: String!) {
  repository(owner: $login, name: $repo) {
    readmeBlob: object(expression: $expression) {
      ... on Blob {
        text
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
        merged_user: dict[str, Any] | None = None
        after: str | None = None
        remaining = request.max_repos
        while remaining > 0:
            page_size = min(request.repo_page_size, remaining)
            payload = await self.execute(
                PROFILE_QUERY,
                {
                    "login": request.username,
                    "repoPageSize": page_size,
                    "after": after,
                    "languageLimit": request.language_limit,
                },
            )
            user = payload.get("data", {}).get("user")
            if user is None:
                raise GitHubClientError("GitHub user not found", status_code=404)
            repositories = user.get("repositories") or {}
            nodes = repositories.get("nodes") or []
            if merged_user is None:
                merged_user = {**user, "repositories": {"nodes": list(nodes)}}
            else:
                merged_user["repositories"]["nodes"].extend(nodes)
            remaining -= len(nodes)
            page_info = repositories.get("pageInfo") or {}
            after = page_info.get("endCursor")
            if not nodes or not page_info.get("hasNextPage") or not after:
                break

        profile = parse_profile_response({"data": {"user": merged_user}}, max_repos=request.max_repos)
        await self._hydrate_readmes(profile, request)
        return profile

    async def query_repository_evidence(self, repo_url: str) -> dict[str, Any]:
        revision = await self.query_repository_revision(repo_url)
        return await self.query_repository_evidence_for_revision(revision)

    async def query_repository_revision(self, repo_url: str) -> dict[str, str]:
        owner, repo = parse_github_repo_url(repo_url)
        repository = await self._request_rest(f"/repos/{owner}/{repo}")
        if repository.get("private"):
            raise GitHubClientError("GitHub repository not found", status_code=404)
        default_branch = str(repository.get("default_branch") or "HEAD")
        commit = await self._request_rest(f"/repos/{owner}/{repo}/commits/{default_branch}")
        commit_sha = str(commit.get("sha") or default_branch)
        return {
            "repo_url": f"https://github.com/{owner}/{repo}",
            "owner": owner,
            "name": repo,
            "default_branch": default_branch,
            "commit_sha": commit_sha,
        }

    async def query_repository_evidence_for_revision(self, revision: dict[str, str]) -> dict[str, Any]:
        owner = revision["owner"]
        repo = revision["name"]
        default_branch = revision["default_branch"]
        commit_sha = revision["commit_sha"]
        tree = await self._request_rest(f"/repos/{owner}/{repo}/git/trees/{commit_sha}", params={"recursive": "1"})
        entries = [
            {
                "path": item.get("path"),
                "type": item.get("type"),
                "size": int(item.get("size") or 0),
            }
            for item in tree.get("tree", [])
            if item.get("type") == "blob" and item.get("path")
        ]
        selected = select_evaluation_paths(entries)
        files = []
        for path in selected:
            content = await self._request_rest(f"/repos/{owner}/{repo}/contents/{path}", params={"ref": default_branch})
            if content.get("encoding") != "base64" or not content.get("content"):
                continue
            raw = base64.b64decode(str(content["content"]), validate=False)
            text = raw[:MAX_EVALUATION_FILE_BYTES].decode("utf-8", errors="replace")
            files.append(
                {
                    "path": path,
                    "size": int(content.get("size") or len(raw)),
                    "truncated": len(raw) > MAX_EVALUATION_FILE_BYTES,
                    "text": text,
                }
            )

        return {
            "repo_url": revision["repo_url"],
            "owner": owner,
            "name": repo,
            "default_branch": default_branch,
            "commit_sha": commit_sha,
            "tree_files": entries,
            "files": files,
        }

    async def _hydrate_readmes(self, profile: dict[str, Any], request: GitHubProfileRequest) -> None:
        candidates = [
            repo
            for repo in profile["repos"]
            if not repo["is_fork"] and not repo["readme_fetched"] and repo.get("name")
        ][: request.readme_limit]
        for repo in candidates:
            readme_path = _readme_path(repo)
            if readme_path is None:
                repo["readme_fetched"] = True
                continue
            payload = await self.execute(
                README_QUERY,
                {
                    "login": request.username,
                    "repo": repo["name"],
                    "expression": f"HEAD:{readme_path}",
                },
            )
            repository = payload.get("data", {}).get("repository") or {}
            readme_text = str((repository.get("readmeBlob") or {}).get("text") or "")
            repo["readme_text"] = readme_text
            repo["readme_fetched"] = True
            repo["has_coverage_badge"] = _has_coverage_badge(readme_text)

    async def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        async with self._semaphore:
            return await self._execute_serialized(query, variables or {})

    async def _request_rest(self, path: str, *, params: dict[str, str] | None = None) -> dict[str, Any]:
        async with self._semaphore:
            response = await self._http_client.get(
                f"{GITHUB_REST_URL}{path}",
                params=params,
                follow_redirects=False,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
        if response.status_code in {403, 429}:
            raise GitHubRateLimitError(
                "GitHub rate limit blocked repository evidence collection",
                status_code=response.status_code,
                retryable=True,
            )
        if response.status_code == 404:
            raise GitHubClientError("GitHub repository not found", status_code=404)
        if response.status_code >= 500:
            raise GitHubClientError(
                f"GitHub REST request failed with status {response.status_code}",
                status_code=response.status_code,
                retryable=True,
            )
        if response.status_code >= 400:
            raise GitHubClientError(
                f"GitHub REST request failed with status {response.status_code}",
                status_code=response.status_code,
                retryable=False,
            )
        return response.json()

    async def _execute_serialized(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        undocumented_failures = 0
        server_failures = 0
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

            if response.status_code >= 500:
                server_failures += 1
                if server_failures >= 3:
                    raise GitHubClientError(
                        f"GitHub GraphQL request failed with status {response.status_code}",
                        status_code=response.status_code,
                        retryable=True,
                    )
                await self._sleep(min(2 ** (server_failures - 1), 4))
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

    pinned_names = {
        node.get("name")
        for node in (user.get("pinnedItems", {}).get("nodes", []) or [])
        if node and node.get("name")
    }
    raw_repos = user.get("repositories", {}).get("nodes", []) or []
    repos = [_parse_repo(repo, pinned_names=pinned_names) for repo in raw_repos]
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


def _parse_repo(repo: dict[str, Any], *, pinned_names: set[str]) -> dict[str, Any]:
    branch_target = ((repo.get("defaultBranchRef") or {}).get("target") or {})
    history = branch_target.get("history") or {}
    oldest_history = branch_target.get("oldestHistory") or {}
    commit_nodes = history.get("nodes") or []
    oldest_commit_nodes = oldest_history.get("nodes") or []
    root_tree = repo.get("rootTree") or repo.get("object") or {}
    entries = root_tree.get("entries") or []
    readme_fetched = "readmeBlob" in repo
    readme_text = str((repo.get("readmeBlob") or {}).get("text") or "")
    first_commit_date = (
        (oldest_commit_nodes[0] or {}).get("committedDate")
        if oldest_commit_nodes
        else repo.get("first_commit_date")
    )

    return {
        "name": repo.get("name"),
        "is_fork": bool(repo.get("isFork")),
        "is_private": bool(repo.get("isPrivate")),
        "is_archived": bool(repo.get("isArchived")),
        "disk_usage": int(repo.get("diskUsage") or 0),
        "pushed_at": repo.get("pushedAt"),
        "stargazer_count": int(repo.get("stargazerCount") or 0),
        "is_pinned": repo.get("name") in pinned_names,
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
        "first_commit_date": first_commit_date,
        "root_entries": [{"name": entry.get("name"), "type": entry.get("type")} for entry in entries],
        "readme_text": readme_text,
        "readme_fetched": readme_fetched,
        "has_coverage_badge": _has_coverage_badge(readme_text),
    }


def _has_coverage_badge(readme_text: str) -> bool:
    readme_lower = readme_text.lower()
    return any(marker in readme_lower for marker in ("codecov", "coveralls", "coverage"))


def _readme_path(repo: dict[str, Any]) -> str | None:
    for entry in repo.get("root_entries", []):
        name = str(entry.get("name") or "")
        if entry.get("type") == "blob" and name.lower().startswith("readme"):
            return name
    return None


def parse_github_repo_url(repo_url: str) -> tuple[str, str]:
    try:
        parsed = urlsplit(repo_url)
        valid_origin = (
            parsed.scheme == "https"
            and parsed.hostname == "github.com"
            and parsed.port in {None, 443}
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError:
        valid_origin = False
    if not valid_origin:
        raise GitHubClientError("Invalid GitHub repository URL", status_code=422)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        raise GitHubClientError("Invalid GitHub repository URL", status_code=422)
    owner, repo = parts
    repo = repo.removesuffix(".git")
    if not _github_name_valid(owner) or not _github_name_valid(repo):
        raise GitHubClientError("Invalid GitHub repository URL", status_code=422)
    return owner, repo


def _github_name_valid(value: str) -> bool:
    if not 1 <= len(value) <= 100:
        return False
    return all(character.isalnum() or character in {"-", "_", "."} for character in value)


def select_evaluation_paths(entries: list[dict[str, Any]], *, limit: int = MAX_EVALUATION_FILES) -> list[str]:
    candidates = [
        entry
        for entry in entries
        if int(entry.get("size") or 0) <= MAX_EVALUATION_FILE_BYTES and _is_text_evaluation_file(str(entry.get("path") or ""))
    ]
    candidates.sort(key=lambda entry: (_path_priority(str(entry["path"])), -int(entry.get("size") or 0), str(entry["path"])))
    return [str(entry["path"]) for entry in candidates[:limit]]


def _is_text_evaluation_file(path: str) -> bool:
    lowered = path.lower()
    if any(part in lowered.split("/") for part in {"node_modules", ".git", ".next", "dist", "build", ".venv"}):
        return False
    return lowered.endswith(
        (
            ".md",
            ".txt",
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".json",
            ".toml",
            ".yaml",
            ".yml",
            ".sql",
            ".html",
            ".css",
            ".rs",
            ".go",
            ".java",
            ".kt",
            ".rb",
            ".php",
            ".cs",
        )
    )


def _path_priority(path: str) -> int:
    lowered = path.lower()
    name = lowered.rsplit("/", 1)[-1]
    if name.startswith("readme"):
        return 0
    if name in {"package.json", "pyproject.toml", "requirements.txt", "poetry.lock", "cargo.toml", "go.mod"}:
        return 1
    if lowered.startswith(".github/workflows/"):
        return 2
    if "/test" in lowered or name.startswith("test_") or ".test." in lowered or ".spec." in lowered:
        return 3
    if name in {"main.py", "app.py", "server.py", "index.ts", "index.tsx", "index.js", "app.ts", "app.tsx"}:
        return 4
    if lowered.startswith(("app/", "src/", "lib/", "components/")):
        return 5
    return 9
