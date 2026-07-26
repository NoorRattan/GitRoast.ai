from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.services.github_client import GitHubGraphQLClient
from app.services.rate_limit import RateLimiterRegistry


def settings_dependency() -> Settings:
    return get_settings()


def cache_client_dependency(request: Request):
    return request.app.state.cache_client


def github_client_dependency(request: Request) -> GitHubGraphQLClient:
    return request.app.state.github_client


def rate_limiters_dependency(request: Request) -> RateLimiterRegistry:
    return request.app.state.rate_limiters


async def db_session_dependency(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        yield session
