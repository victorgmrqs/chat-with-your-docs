import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.mark.parametrize(("enabled", "status"), [(True, 200), (False, 404)])
@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_docs_follow_the_flag(
    unreachable_settings: Settings, path: str, enabled: bool, status: int
) -> None:
    settings = unreachable_settings.model_copy(update={"api_docs_enabled": enabled})

    # No `with`: the docs routes exist from construction, the lifespan is not needed.
    response = TestClient(create_app(settings=settings)).get(path)

    assert response.status_code == status


def test_api_docs_flag_read_from_env_without_full_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`app = create_app()` runs at import, before the full Settings exist."""
    monkeypatch.setenv("API_DOCS_ENABLED", "false")

    assert create_app().openapi_url is None


def test_openapi_schema_still_exported_when_disabled(unreachable_settings: Settings) -> None:
    """scripts/export_openapi.py calls app.openapi(), which does not need the route."""
    settings = unreachable_settings.model_copy(update={"api_docs_enabled": False})

    schema = create_app(settings=settings).openapi()

    assert "/chat" in schema["paths"]
