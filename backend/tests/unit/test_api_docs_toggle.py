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


PROXIED = {"X-Forwarded-Prefix": "/api"}  # what nginx sends on /api/* (CWYD-20)


def test_api_docs_through_the_web_server_use_the_api_prefix(
    unreachable_settings: Settings,
) -> None:
    client = TestClient(create_app(settings=unreachable_settings))

    page = client.get("/docs", headers=PROXIED)
    spec = client.get("/openapi.json", headers=PROXIED)

    assert page.status_code == 200
    assert "url: '/api/openapi.json'" in page.text  # Swagger UI asks through the proxy
    assert spec.json()["servers"] == [{"url": "/api"}]  # "Try it out" calls /api/...


def test_api_docs_called_directly_keep_plain_paths(unreachable_settings: Settings) -> None:
    """:8000/docs has no proxy header: the page loads /openapi.json, which exists there."""
    client = TestClient(create_app(settings=unreachable_settings))

    page = client.get("/docs")
    spec = client.get("/openapi.json")

    assert "url: '/openapi.json'" in page.text
    assert "servers" not in spec.json()


def test_forwarded_prefix_other_than_the_configured_one_is_ignored(
    unreachable_settings: Settings,
) -> None:
    client = TestClient(create_app(settings=unreachable_settings))

    page = client.get("/docs", headers={"X-Forwarded-Prefix": "/evil"})

    assert "url: '/openapi.json'" in page.text


def test_api_routes_answer_through_the_web_server(unreachable_settings: Settings) -> None:
    client = TestClient(create_app(settings=unreachable_settings))

    assert client.get("/health", headers=PROXIED).json() == {"status": "ok"}


def test_api_docs_disabled_through_the_web_server(unreachable_settings: Settings) -> None:
    settings = unreachable_settings.model_copy(update={"api_docs_enabled": False})
    client = TestClient(create_app(settings=settings))

    assert [client.get(p, headers=PROXIED).status_code for p in ("/docs", "/openapi.json")] == [
        404,
        404,
    ]


@pytest.mark.parametrize(("method", "path"), [("GET", "/api/health"), ("POST", "/api/chat")])
def test_proxied_path_that_already_has_the_prefix_is_not_routed(
    unreachable_settings: Settings, method: str, path: str
) -> None:
    """nginx strips one /api: /api/api/chat would skip its rate-limited locations (DOM-27)."""
    client = TestClient(create_app(settings=unreachable_settings))

    response = client.request(method, path, headers=PROXIED, json={"question": "q"})

    assert response.status_code == 404


def test_proxied_trailing_slash_redirect_keeps_the_prefix(unreachable_settings: Settings) -> None:
    """/api/chat/ falls outside nginx's exact location; the redirect must lead back into it."""
    client = TestClient(create_app(settings=unreachable_settings), follow_redirects=False)

    response = client.post("/chat/", headers=PROXIED, json={"question": "q"})

    assert response.status_code == 307
    assert response.headers["location"].endswith("/api/chat")
