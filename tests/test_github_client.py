import os

import pytest

from app.services.github_client import (
    GitHubGraphQLClient,
    GitHubRateLimitError,
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

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
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


async def test_query_user_profile_uses_injected_client_and_caps_whale_repos(load_github_fixture):
    stub = StubAsyncClient([StubResponse(200, load_github_fixture("whale_profile.json"))])
    client = GitHubGraphQLClient("token", stub, max_repos=3)

    profile = await client.query_user_profile("whaledev")

    assert [repo["name"] for repo in profile["repos"]] == ["repo-newest", "repo-2", "repo-3"]
    assert len(stub.calls) == 1
    assert stub.calls[0][1]["json"]["variables"]["maxRepos"] == 3


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


async def test_undocumented_secondary_limit_raises_after_third_failure():
    slept = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    stub = StubAsyncClient([StubResponse(429), StubResponse(429), StubResponse(429)])
    client = GitHubGraphQLClient("token", stub, sleep=fake_sleep)

    with pytest.raises(GitHubRateLimitError):
        await client.execute("query { viewer { login } }")

    assert slept == [1, 2]
    assert len(stub.calls) == 3
