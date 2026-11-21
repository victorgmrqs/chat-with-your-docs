from app.main import create_app
from fastapi.testclient import TestClient

from app.config import Settings


def test_health_returns_ok_without_touching_the_database(unreachable_settings: Settings) -> None:
    with TestClient(create_app(settings=unreachable_settings)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
