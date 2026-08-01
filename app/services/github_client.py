import asyncio
import base64
import logging
import re
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx


GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
GITHUB_REST_URL = "https://api.github.com"
MAX_EVALUATION_FILES = 28
MAX_EVALUATION_FILE_BYTES = 40_000
MAX_TRANSIENT_RETRIES = 3

logger = logging.getLogger(__name__)


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

EXTERNAL_PULL_REQUESTS_QUERY = """
query GitRoastExternalPullRequests($query: String!) {
  search(type: ISSUE, query: $query, first: 1) {
    issueCount
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
        self._rate_limit_remaining: ContextVar[int | None] = ContextVar("github_rate_limit_remaining", default=None)

    @property
    def last_rate_limit_remaining(self) -> int | None:
        return self._rate_limit_remaining.get()

    async def query_user_profile(self, username: str, *, max_repos: int | None = None) -> dict[str, Any]:
        self._rate_limit_remaining.set(None)
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
        try:
            profile["external_pr_count"] = await self._query_external_pull_request_count(profile["username"])
        except GitHubClientError:
            # Missing evidence must not unlock harsher roast intensities.
            profile["external_pr_count"] = 0
            logger.warning(
                "external pull request lookup unavailable; applying beginner safeguard",
                exc_info=True,
                extra={"username": profile["username"]},
            )
        await self._hydrate_first_commit_dates(profile, request)
        await self._hydrate_readmes(profile, request)
        return profile

    async def _query_external_pull_request_count(self, username: str) -> int:
        payload = await self.execute(
            EXTERNAL_PULL_REQUESTS_QUERY,
            {"query": f"is:pr author:{username} -user:{username}"},
        )
        search = payload.get("data", {}).get("search") or {}
        return max(0, int(search.get("issueCount") or 0))

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

    async def _hydrate_first_commit_dates(self, profile: dict[str, Any], request: GitHubProfileRequest) -> None:
        """Fill the default-branch lower bound without invalid GraphQL backward pagination.

        The profile query already includes up to 20 newest commits. For short histories,
        its final node is the oldest commit. Longer histories need one lightweight REST
        page request plus, when paginated, a single request for the last page.
        """
        for repo in profile["repos"]:
            if repo.get("is_fork") or not repo.get("name") or repo.get("first_commit_date"):
                continue
            commit_dates = repo.get("commit_dates") or []
            commit_count = int(repo.get("commit_count") or 0)
            if commit_dates and commit_count <= len(commit_dates):
                repo["first_commit_date"] = commit_dates[-1]
                continue
            if commit_count > 0:
                first_commit_date = await self._fetch_oldest_default_branch_commit(
                    request.username,
                    str(repo["name"]),
                )
                if first_commit_date:
                    repo["first_commit_date"] = first_commit_date

    async def _fetch_oldest_default_branch_commit(self, owner: str, repo: str) -> str | None:
        response = await self._request_rest_response(
            f"/repos/{owner}/{repo}/commits",
            params={"per_page": "1"},
        )
        commits = response.json()
        if not isinstance(commits, list) or not commits:
            return None

        last_page = _last_link_page(response.headers.get("Link"))
        if last_page is not None:
            response = await self._request_rest_response(
                f"/repos/{owner}/{repo}/commits",
                params={"per_page": "1", "page": str(last_page)},
            )
            commits = response.json()
            if not isinstance(commits, list) or not commits:
                return None
        commit = commits[0] if isinstance(commits[0], dict) else {}
        metadata = commit.get("commit") if isinstance(commit, dict) else {}
        committer = metadata.get("committer") if isinstance(metadata, dict) else {}
        author = metadata.get("author") if isinstance(metadata, dict) else {}
        return str((committer or {}).get("date") or (author or {}).get("date") or "") or None

    async def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        async with self._semaphore:
            return await self._execute_serialized(query, variables or {})

    async def _request_rest(self, path: str, *, params: dict[str, str] | None = None) -> dict[str, Any]:
        response = await self._request_rest_response(path, params=params)
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    async def _request_rest_response(self, path: str, *, params: dict[str, str] | None = None):
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
        self._record_rate_limit_remaining(response)
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
        return response

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
            self._record_rate_limit_remaining(response)

            if response.status_code in {403, 429}:
                retry_after = response.headers.get("Retry-After")
                if retry_after is not None:
                    await self._sleep(int(retry_after))
                    continue

                undocumented_failures += 1
                if undocumented_failures > MAX_TRANSIENT_RETRIES:
                    raise GitHubRateLimitError(
                        "GitHub secondary rate limit did not include Retry-After",
                        status_code=response.status_code,
                        retryable=True,
                    )
                await self._sleep(min(2 ** (undocumented_failures - 1), 8))
                continue

            if response.status_code >= 500:
                server_failures += 1
                if server_failures > MAX_TRANSIENT_RETRIES:
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

    def _record_rate_limit_remaining(self, response: Any) -> None:
        value = response.headers.get("X-RateLimit-Remaining")
        if value is None:
            return
        try:
            remaining = int(value)
        except (TypeError, ValueError):
            return
        if remaining >= 0:
            self._rate_limit_remaining.set(remaining)


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


def _last_link_page(link_header: str | None) -> int | None:
    if not link_header:
        return None
    for url, relation in re.findall(r'<([^>]+)>;\s*rel="([^"]+)"', link_header):
        if relation != "last":
            continue
        page = parse_qs(urlsplit(url).query).get("page", [None])[0]
        try:
            parsed_page = int(page) if page is not None else None
        except ValueError:
            return None
        return parsed_page if parsed_page and parsed_page > 1 else None
    return None


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
    if limit <= 0:
        return []

    selected: list[dict[str, Any]] = []
    selected_paths: set[str] = set()
    priority_budgets = {0: 1, 1: 3, 2: 1}
    priority_counts = {priority: 0 for priority in priority_budgets}

    # Preserve a compact project overview before sampling implementation files.
    for entry in candidates:
        priority = _path_priority(str(entry["path"]))
        if priority not in priority_budgets or priority_counts[priority] >= priority_budgets[priority]:
            continue
        selected.append(entry)
        selected_paths.add(str(entry["path"]))
        priority_counts[priority] += 1
        if len(selected) == limit:
            return [str(item["path"]) for item in selected]

    # Monorepos should not lose entire top-level packages to global path priority.
    remaining = [entry for entry in candidates if str(entry["path"]) not in selected_paths]
    for directory in sorted({_sample_directory(str(entry["path"])) for entry in remaining}):
        entry = next(item for item in remaining if _sample_directory(str(item["path"])) == directory)
        selected.append(entry)
        selected_paths.add(str(entry["path"]))
        if len(selected) == limit:
            return [str(item["path"]) for item in selected]

    for entry in candidates:
        path = str(entry["path"])
        if path in selected_paths:
            continue
        selected.append(entry)
        selected_paths.add(path)
        if len(selected) == limit:
            break
    return [str(item["path"]) for item in selected]


def _sample_directory(path: str) -> str:
    parts = path.split("/")
    if len(parts) < 2:
        return "."
    if parts[0] in {"apps", "crates", "modules", "packages", "services"} and len(parts) >= 3:
        return "/".join(parts[:2])
    return parts[0]


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
