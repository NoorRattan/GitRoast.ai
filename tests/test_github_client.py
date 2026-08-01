import base64
import os

import pytest

from app.services.github_client import (
    GitHubGraphQLClient,
    GitHubRateLimitError,
    EXTERNAL_PULL_REQUESTS_QUERY,
    PROFILE_QUERY,
    README_QUERY,
    parse_github_repo_url,
    parse_profile_response,
)


class StubResponse:
    def __init__(self, status_code: int, payload: dict | None = None, headers: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}

    def json(self):
        return self._payload


class StubAsyncClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.get_calls = []

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)

    async def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        return self.responses.pop(0)


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("GITHUB_PAT"), reason="GITHUB_PAT is not set")
async def test_github_pat_can_read_public_torvalds_linux_repo():
    query = """
    query {
      repository(owner: "torvalds", name: "linux") {
        name
      }
    }
    """
    import httpx

    async with httpx.AsyncClient(timeout=20) as http_client:
        client = GitHubGraphQLClient(os.environ["GITHUB_PAT"], http_client)
        payload = await client.execute(query)

    assert payload["data"]["repository"]["name"] == "linux"


@pytest.mark.parametrize(
    "fixture_name",
    ["small_profile.json", "whale_profile.json", "beginner_account.json", "forked_only.json"],
)
def test_parse_profile_response_handles_fixture_shapes(load_github_fixture, fixture_name):
    profile = parse_profile_response(load_github_fixture(fixture_name))

    assert profile["username"]
    assert "avatar_url" in profile
    assert isinstance(profile["repos"], list)
    assert all("languages" in repo for repo in profile["repos"])


def test_profile_query_and_parser_use_real_github_fields(load_github_fixture):
    assert "pinnedItems(first: 6, types: REPOSITORY)" in PROFILE_QUERY
    assert "readmeBlob: object(expression: $expression)" in README_QUERY
    assert "issueCount" in EXTERNAL_PULL_REQUESTS_QUERY
    assert "oldestHistory" not in PROFILE_QUERY
    assert "readmeBlob" not in PROFILE_QUERY
    assert "isPinned" not in PROFILE_QUERY

    profile = parse_profile_response(load_github_fixture("small_profile.json"))
    repos = {repo["name"]: repo for repo in profile["repos"]}

    assert repos["api-service"]["is_pinned"] is True
    assert "Installation" in repos["api-service"]["readme_text"]
    assert repos["api-service"]["has_coverage_badge"] is True
    assert repos["infra-playbook"]["is_pinned"] is False


@pytest.mark.parametrize(
    "repo_url",
    [
        "http://github.com/example/repo",
        "https://github.com@attacker.example/example/repo",
        "https://github.com/example/repo?redirect=https://attacker.example",
        "https://github.com/example/repo/extra",
        "https://api.github.com/example/repo",
    ],
)
def test_parse_github_repo_url_rejects_untrusted_or_ambiguous_urls(repo_url):
    with pytest.raises(Exception):
        parse_github_repo_url(repo_url)


def test_parse_github_repo_url_canonicalizes_dot_git_suffix():
    assert parse_github_repo_url("https://github.com/example/repo.git") == ("example", "repo")


@pytest.mark.asyncio
async def test_repository_evidence_fetches_every_file_at_resolved_commit():
    commit_sha = "resolved-commit-sha"
    stub = StubAsyncClient(
        [
            StubResponse(
                200,
                {
                    "tree": [
                        {"path": "README.md", "type": "blob", "size": 20},
                    ]
                },
            ),
            StubResponse(
                200,
                {
                    "encoding": "base64",
                    "content": base64.b64encode(b"# Example\n").decode("ascii"),
                    "size": 10,
                },
            ),
        ]
    )
    client = GitHubGraphQLClient("token", stub)

    evidence = await client.query_repository_evidence_for_revision(
        {
            "repo_url": "https://github.com/example/repo",
            "owner": "example",
            "name": "repo",
            "default_branch": "main",
            "commit_sha": commit_sha,
        }
    )

    assert evidence["commit_sha"] == commit_sha
    assert stub.get_calls[1][1]["params"] == {"ref": commit_sha}


def test_parse_profile_response_keeps_oldest_default_branch_commit():
    profile = parse_profile_response(
        {
            "data": {
                "user": {
                    "login": "longrunner",
                    "createdAt": "2019-01-01T00:00:00Z",
                    "avatarUrl": None,
                    "pullRequests": {"totalCount": 0},
                    "pinnedItems": {"nodes": []},
                    "repositories": {
                        "nodes": [
                            {
                                "name": "flagship",
                                "isFork": False,
                                "isPrivate": False,
                                "isArchived": False,
                                "languages": {"edges": []},
                                "defaultBranchRef": {
                                    "target": {
                                        "history": {
                                            "totalCount": 500,
                                            "nodes": [
                                                {
                                                    "committedDate": "2026-07-01T00:00:00Z",
                                                    "messageHeadline": "Add release verification",
                                                }
                                            ],
                                        },
                                    }
                                },
                                "first_commit_date": "2020-01-01T00:00:00Z",
                                "rootTree": {"entries": []},
                            }
                        ]
                    },
                }
            }
        }
    )

    assert profile["repos"][0]["first_commit_date"] == "2020-01-01T00:00:00Z"


async def test_query_user_profile_fetches_oldest_commit_for_long_default_branch_history():
    profile_payload = {
        "data": {
            "user": {
                "login": "longrunner",
                "createdAt": "2019-01-01T00:00:00Z",
                "avatarUrl": None,
                "pullRequests": {"totalCount": 0},
                "pinnedItems": {"nodes": []},
                "repositories": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {
                            "name": "flagship",
                            "isFork": False,
                            "isPrivate": False,
                            "isArchived": False,
                            "rootTree": {"entries": []},
                            "languages": {"edges": []},
                            "defaultBranchRef": {
                                "target": {
                                    "history": {
                                        "totalCount": 500,
                                        "nodes": [{"committedDate": "2026-07-01T00:00:00Z", "messageHeadline": "Recent change"}],
                                    }
                                }
                            },
                        }
                    ],
                },
            }
        }
    }
    stub = StubAsyncClient(
        [
            StubResponse(200, profile_payload),
            StubResponse(200, {"data": {"search": {"issueCount": 2}}}),
            StubResponse(200, [{"commit": {"committer": {"date": "2026-07-01T00:00:00Z"}}}], headers={"Link": '<https://api.github.com/repos/longrunner/flagship/commits?per_page=1&page=500>; rel="last"'}),
            StubResponse(200, [{"commit": {"committer": {"date": "2020-01-01T00:00:00Z"}}}]),
        ]
    )
    client = GitHubGraphQLClient("token", stub, max_repos=1)

    profile = await client.query_user_profile("longrunner")

    assert profile["repos"][0]["first_commit_date"] == "2020-01-01T00:00:00Z"
    assert profile["external_pr_count"] == 2
    assert len(stub.get_calls) == 2
    assert stub.get_calls[1][1]["params"] == {"per_page": "1", "page": "500"}


async def test_query_user_profile_uses_injected_client_and_caps_whale_repos(load_github_fixture):
    payload = load_github_fixture("whale_profile.json")
    for repo in payload["data"]["user"]["repositories"]["nodes"]:
        repo["first_commit_date"] = "2020-01-01T00:00:00Z"
    stub = StubAsyncClient([StubResponse(200, payload), StubResponse(200, {"data": {"search": {"issueCount": 4}}})])
    client = GitHubGraphQLClient("token", stub, max_repos=3)

    profile = await client.query_user_profile("whaledev")

    assert [repo["name"] for repo in profile["repos"]] == ["repo-newest", "repo-2", "repo-3"]
    assert len(stub.calls) == 2
    assert stub.calls[0][1]["json"]["variables"]["repoPageSize"] == 3
    assert stub.calls[1][1]["json"]["variables"]["query"] == "is:pr author:whaledev -user:whaledev"


async def test_query_user_profile_paginates_large_repository_sets():
    def page(name: str, cursor: str | None, has_next: bool) -> dict:
        return {
            "data": {
                "user": {
                    "login": "large",
                    "createdAt": "2020-01-01T00:00:00Z",
                    "avatarUrl": None,
                    "pullRequests": {"totalCount": 0},
                    "pinnedItems": {"nodes": []},
                    "repositories": {
                        "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
                        "nodes": [
                            {
                                "name": name,
                                "isFork": True,
                                "isPrivate": False,
                                "isArchived": False,
                                "rootTree": {"entries": []},
                                "languages": {"edges": []},
                            }
                        ],
                    },
                }
            }
        }

    stub = StubAsyncClient(
        [
            StubResponse(200, page("newer", "cursor-1", True)),
            StubResponse(200, page("older", None, False)),
            StubResponse(200, {"data": {"search": {"issueCount": 1}}}),
        ]
    )
    client = GitHubGraphQLClient("token", stub, max_repos=2)

    profile = await client.query_user_profile("large")

    assert [repo["name"] for repo in profile["repos"]] == ["newer", "older"]
    assert stub.calls[1][1]["json"]["variables"]["after"] == "cursor-1"
    assert profile["external_pr_count"] == 1


async def test_retry_after_is_respected_before_retry(load_github_fixture):
    slept = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    stub = StubAsyncClient(
        [
            StubResponse(429, headers={"Retry-After": "2"}),
            StubResponse(200, load_github_fixture("small_profile.json")),
        ]
    )
    client = GitHubGraphQLClient("token", stub, sleep=fake_sleep)

    payload = await client.execute("query { viewer { login } }")

    assert payload["data"]["user"]["login"] == "cleanbuilder"
    assert slept == [2]
    assert len(stub.calls) == 2


async def test_undocumented_secondary_limit_allows_three_retries_before_raising():
    slept = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    stub = StubAsyncClient([StubResponse(429), StubResponse(429), StubResponse(429), StubResponse(429)])
    client = GitHubGraphQLClient("token", stub, sleep=fake_sleep)

    with pytest.raises(GitHubRateLimitError):
        await client.execute("query { viewer { login } }")

    assert slept == [1, 2, 4]
    assert len(stub.calls) == 4


async def test_query_user_profile_fails_safe_when_external_pr_lookup_is_unavailable(load_github_fixture, caplog):
    payload = load_github_fixture("small_profile.json")
    for repo in payload["data"]["user"]["repositories"]["nodes"]:
        repo["first_commit_date"] = "2020-01-01T00:00:00Z"
    stub = StubAsyncClient([StubResponse(200, payload), StubResponse(429), StubResponse(429), StubResponse(429), StubResponse(429)])
    slept = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    client = GitHubGraphQLClient("token", stub, max_repos=3, sleep=fake_sleep)

    profile = await client.query_user_profile("cleanbuilder")

    assert profile["external_pr_count"] == 0
    assert "beginner safeguard" in caplog.text
    assert slept == [1, 2, 4]


async def test_query_user_profile_records_last_known_github_rate_limit(load_github_fixture):
    payload = load_github_fixture("small_profile.json")
    for repo in payload["data"]["user"]["repositories"]["nodes"]:
        repo["first_commit_date"] = "2020-01-01T00:00:00Z"
    stub = StubAsyncClient(
        [
            StubResponse(200, payload, headers={"X-RateLimit-Remaining": "321"}),
            StubResponse(200, {"data": {"search": {"issueCount": 4}}}, headers={"X-RateLimit-Remaining": "320"}),
        ]
    )
    client = GitHubGraphQLClient("token", stub, max_repos=3)

    await client.query_user_profile("cleanbuilder")

    assert client.last_rate_limit_remaining == 320


async def test_transient_server_failure_retries_before_success(load_github_fixture):
    slept = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    stub = StubAsyncClient(
        [
            StubResponse(502),
            StubResponse(200, load_github_fixture("small_profile.json")),
        ]
    )
    client = GitHubGraphQLClient("token", stub, sleep=fake_sleep)

    payload = await client.execute("query { viewer { login } }")

    assert payload["data"]["user"]["login"] == "cleanbuilder"
    assert slept == [1]
