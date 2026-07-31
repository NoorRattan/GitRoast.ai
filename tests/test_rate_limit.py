import pytest
from starlette.requests import Request

from app.services.rate_limit import InMemoryFixedWindowLimiter, RateLimiterRegistry, client_ip


def _request(headers=None):
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers or [],
            "client": ("10.0.0.8", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
            "root_path": "",
            "http_version": "1.1",
        }
    )


def test_client_ip_uses_only_trusted_gateway_identity():
    request = _request(headers=[(b"cf-connecting-ip", b"203.0.113.77")])
    request.state.gateway_client_ip = "198.51.100.15"

    assert client_ip(request) == "198.51.100.15"


def test_client_ip_ignores_untrusted_or_missing_gateway_identity():
    request = _request(headers=[(b"cf-connecting-ip", b"not-an-ip")])

    assert client_ip(request) == "unknown"


def test_client_ip_ignores_untrusted_forwarded_header():
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"x-forwarded-for", b"203.0.113.77")],
            "client": ("10.0.0.8", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
            "root_path": "",
            "http_version": "1.1",
        }
    )

    assert client_ip(request) == "unknown"


@pytest.mark.asyncio
async def test_github_capacity_guard_fails_open_when_its_limiter_errors(caplog):
    class BrokenLimiter:
        async def limit(self, _identifier):
            raise RuntimeError("upstash unavailable")

    registry = RateLimiterRegistry({"github_capacity": BrokenLimiter()}, github_capacity_mode="enforce")

    result = await registry.check_global("github_capacity")

    assert result is None
    assert "allowing request" in caplog.text


@pytest.mark.asyncio
async def test_github_capacity_guard_shadows_a_would_be_block(caplog):
    registry = RateLimiterRegistry(
        {"github_capacity": InMemoryFixedWindowLimiter(0, 3600)},
        github_capacity_mode="shadow",
    )

    result = await registry.check_global("github_capacity")

    assert result is not None
    assert result.allowed is False
    assert "shadow mode" in caplog.text
