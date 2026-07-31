import asyncio
from ipaddress import ip_address
import logging
import time
from dataclasses import dataclass
from typing import Protocol

from fastapi import Request

from app.core.errors import APIError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset: int


class AsyncRateLimiter(Protocol):
    async def limit(self, identifier: str) -> RateLimitResult:
        ...


class UpstashFixedWindowLimiter:
    def __init__(self, redis_url: str, redis_token: str, *, max_requests: int, window_seconds: int, prefix: str) -> None:
        from upstash_ratelimit import FixedWindow, Ratelimit
        from upstash_redis import Redis

        redis = Redis(url=redis_url, token=redis_token)
        self._limiter = Ratelimit(
            redis=redis,
            limiter=FixedWindow(max_requests=max_requests, window=window_seconds, unit="s"),
            prefix=prefix,
        )

    async def limit(self, identifier: str) -> RateLimitResult:
        response = await asyncio.to_thread(self._limiter.limit, identifier)
        return RateLimitResult(
            allowed=response.allowed,
            limit=response.limit,
            remaining=response.remaining,
            reset=response.reset,
        )


class InMemoryFixedWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._counts: dict[str, tuple[int, int]] = {}

    async def limit(self, identifier: str) -> RateLimitResult:
        window = int(time.time() // self._window_seconds)
        current_window, count = self._counts.get(identifier, (window, 0))
        if current_window != window:
            current_window, count = window, 0
        count += 1
        self._counts[identifier] = (current_window, count)
        reset = (current_window + 1) * self._window_seconds
        return RateLimitResult(
            allowed=count <= self._max_requests,
            limit=self._max_requests,
            remaining=max(0, self._max_requests - count),
            reset=reset,
        )

    def reset(self) -> None:
        self._counts.clear()


class RateLimiterRegistry:
    def __init__(self, limiters: dict[str, AsyncRateLimiter], *, github_capacity_mode: str = "enforce") -> None:
        self._limiters = limiters
        self._github_capacity_mode = github_capacity_mode

    async def check(self, policy: str, request: Request) -> RateLimitResult:
        limiter = self._limiters[policy]
        identifier = f"{policy}:{client_ip(request)}"
        result = await limiter.limit(identifier)
        request.state.rate_limit_result = result
        if not result.allowed:
            raise APIError(429, "rate_limited", "Too many requests. Try again later.")
        return result

    async def check_global(self, policy: str, request: Request | None = None) -> RateLimitResult | None:
        try:
            result = await self._limiters[policy].limit(f"{policy}:global")
        except Exception:
            logger.warning("GitHub capacity guard unavailable; allowing request", exc_info=True, extra={"policy": policy})
            return None
        if request is not None:
            request.state.capacity_limit_result = result
        if not result.allowed:
            if self._github_capacity_mode == "shadow":
                logger.warning(
                    "GitHub capacity guard would block request in shadow mode",
                    extra={"policy": policy, "limit": result.limit, "remaining": result.remaining, "reset": result.reset},
                )
                return result
            raise APIError(429, "capacity_limited", "GitHub capacity is temporarily exhausted. Try again later.")
        return result


def client_ip(request: Request) -> str:
    value = getattr(request.state, "gateway_client_ip", None)
    return value if isinstance(value, str) and _valid_ip(value) else "unknown"


def _valid_ip(value: str) -> bool:
    try:
        ip_address(value)
    except ValueError:
        return False
    return True


def create_rate_limiters(
    redis_url: str,
    redis_token: str,
    *,
    github_capacity_per_hour: int,
    github_capacity_mode: str,
) -> RateLimiterRegistry:
    return RateLimiterRegistry(
        {
            "post_audit": UpstashFixedWindowLimiter(
                redis_url,
                redis_token,
                max_requests=20,
                window_seconds=3600,
                prefix="gitroast:ratelimit:post_audit",
            ),
            "opt_out": UpstashFixedWindowLimiter(
                redis_url,
                redis_token,
                max_requests=5,
                window_seconds=86400,
                prefix="gitroast:ratelimit:opt_out",
            ),
            "get_audit": UpstashFixedWindowLimiter(
                redis_url,
                redis_token,
                max_requests=120,
                window_seconds=3600,
                prefix="gitroast:ratelimit:get_audit",
            ),
            "card_data": UpstashFixedWindowLimiter(
                redis_url,
                redis_token,
                max_requests=300,
                window_seconds=3600,
                prefix="gitroast:ratelimit:card_data",
            ),
            "project_evaluation": UpstashFixedWindowLimiter(
                redis_url,
                redis_token,
                max_requests=10,
                window_seconds=3600,
                prefix="gitroast:ratelimit:project_evaluation",
            ),
            "admin_auth": UpstashFixedWindowLimiter(
                redis_url,
                redis_token,
                max_requests=10,
                window_seconds=3600,
                prefix="gitroast:ratelimit:admin_auth",
            ),
            "github_capacity": UpstashFixedWindowLimiter(
                redis_url,
                redis_token,
                max_requests=github_capacity_per_hour,
                window_seconds=3600,
                prefix="gitroast:ratelimit:github_capacity",
            ),
        },
        github_capacity_mode=github_capacity_mode,
    )
