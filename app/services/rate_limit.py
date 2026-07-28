import asyncio
import time
from dataclasses import dataclass
from typing import Protocol

from fastapi import Request

from app.core.errors import APIError


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
    def __init__(self, limiters: dict[str, AsyncRateLimiter]) -> None:
        self._limiters = limiters

    async def check(self, policy: str, request: Request) -> None:
        limiter = self._limiters[policy]
        identifier = f"{policy}:{client_ip(request)}"
        result = await limiter.limit(identifier)
        if not result.allowed:
            raise APIError(429, "rate_limited", "Too many requests. Try again later.")


def client_ip(request: Request) -> str:
    # Uvicorn resolves proxy headers only for its configured trusted proxy
    # addresses. Reading X-Forwarded-For again here would bypass that boundary.
    return request.client.host if request.client else "unknown"


def create_rate_limiters(redis_url: str, redis_token: str) -> RateLimiterRegistry:
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
        }
    )
