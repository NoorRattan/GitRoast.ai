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
