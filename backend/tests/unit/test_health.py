from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_returns_ok_without_touching_the_database(unreachable_settings: Settings) -> None:
    with TestClient(create_app(settings=unreachable_settings)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_documents_the_503_response(unreachable_settings: Settings) -> None:
    with TestClient(create_app(settings=unreachable_settings)) as client:
        schema = client.get("/openapi.json").json()

    responses = schema["paths"]["/health/ready"]["get"]["responses"]
    assert "503" in responses
    assert responses["503"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }
