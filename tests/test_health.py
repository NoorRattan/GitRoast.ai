from fastapi.testclient import TestClient


def test_health_route_boots_and_returns_static_200(required_env):
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_versioned_health_exposes_active_scoring_schema(required_env):
    from app.core.config import get_settings
    from app.services.scoring_constants import SCHEMA_VERSION

    get_settings.cache_clear()
    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "schema_version": SCHEMA_VERSION}


def test_direct_backend_api_rejects_forged_cloudflare_identity(required_env):
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import create_app

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/audit",
            json={"username": "octocat", "roast_intensity": "mild"},
            headers={"cf-connecting-ip": "203.0.113.8", "x-forwarded-for": "203.0.113.9"},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "origin_forbidden"
