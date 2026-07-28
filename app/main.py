from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.db.session import close_db, init_db
from app.routers import admin, audit, card_data, health, opt_out, project_evaluation
from app.services.cache import create_upstash_client
from app.services.github_client import GitHubGraphQLClient
from app.services.rate_limit import create_rate_limiters


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    http_client = httpx.AsyncClient(timeout=20)
    app.state.http_client = http_client
    app.state.github_client = GitHubGraphQLClient(settings.github_pat, http_client)
    app.state.cache_client = create_upstash_client(settings.upstash_url, settings.upstash_token)
    app.state.rate_limiters = create_rate_limiters(settings.upstash_url, settings.upstash_token)
    app.state.session_factory = init_db(settings)
    app.state.refresh_locks = set()
    app.state.refresh_scheduled_count = 0
    try:
        yield
    finally:
        await http_client.aclose()
        await close_db()


def create_app() -> FastAPI:
    settings = get_settings()
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            enable_tracing=False,
            send_default_pii=False,
        )
    app = FastAPI(title="GitRoast.ai API", lifespan=lifespan)
    install_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(audit.router)
    app.include_router(card_data.router)
    app.include_router(opt_out.router)
    app.include_router(project_evaluation.router)
    app.include_router(admin.router)
    return app


app = create_app()
