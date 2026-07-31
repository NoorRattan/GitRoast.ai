from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from ipaddress import ip_address
import secrets
import time

import httpx
import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.errors import error_payload, install_error_handlers
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
    app.state.rate_limiters = create_rate_limiters(
        settings.upstash_url,
        settings.upstash_token,
        github_capacity_per_hour=settings.github_capacity_per_hour,
        github_capacity_mode=settings.github_capacity_mode,
    )
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

    @app.middleware("http")
    async def require_trusted_gateway(request, call_next):
        protected = request.url.path.startswith("/api/v1/") and request.url.path != "/api/v1/health"
        if protected:
            supplied_secret = request.headers.get("x-gitroast-gateway-secret", "")
            client_ip = request.headers.get("x-gitroast-client-ip", "")
            if not secrets.compare_digest(supplied_secret, settings.gateway_shared_secret):
                return JSONResponse(status_code=403, content=error_payload("origin_forbidden", "Use the configured API gateway."))
            try:
                ip_address(client_ip)
            except ValueError:
                return JSONResponse(status_code=403, content=error_payload("origin_forbidden", "The gateway client identity is invalid."))
            request.state.gateway_client_ip = client_ip

        response = await call_next(request)
        result = getattr(request.state, "rate_limit_result", None)
        if response.status_code == 429:
            result = getattr(request.state, "capacity_limit_result", result)
        if result is not None:
            response.headers["RateLimit-Limit"] = str(result.limit)
            response.headers["RateLimit-Remaining"] = str(result.remaining)
            response.headers["RateLimit-Reset"] = str(result.reset)
            if response.status_code == 429:
                response.headers["Retry-After"] = str(max(1, result.reset - int(time.time())))
        return response
    app.include_router(health.router)
    app.include_router(audit.router)
    app.include_router(card_data.router)
    app.include_router(opt_out.router)
    app.include_router(project_evaluation.router)
    app.include_router(admin.router)
    return app


app = create_app()
