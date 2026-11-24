"""DOM-23: a request id on every response and in every error body (no database needed)."""

import uuid

from fastapi.testclient import TestClient

from app.api.errors import INTERNAL_ERROR_DETAIL
from app.api.request_id import REQUEST_ID_HEADER
from app.config import Settings
from app.main import create_app

PRIVATE_TEXT = "chunk text that must never reach a client"


def test_request_id_on_success_response(unreachable_settings: Settings) -> None:
    with TestClient(create_app(settings=unreachable_settings)) as client:
        first = client.get("/health")
        second = client.get("/health")

    assert uuid.UUID(first.headers[REQUEST_ID_HEADER])
    assert first.headers[REQUEST_ID_HEADER] != second.headers[REQUEST_ID_HEADER]


def test_request_id_ignores_client_supplied_id(unreachable_settings: Settings) -> None:
    supplied = str(uuid.uuid4())

    with TestClient(create_app(settings=unreachable_settings)) as client:
        response = client.get("/health", headers={REQUEST_ID_HEADER: supplied})

    assert response.headers[REQUEST_ID_HEADER] != supplied


def test_request_id_in_domain_error_body(unreachable_settings: Settings) -> None:
    with TestClient(create_app(settings=unreachable_settings)) as client:
        response = client.post("/chat", json={"question": "   "})

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "empty_question"
    assert body["request_id"] == response.headers[REQUEST_ID_HEADER]


def test_request_id_unexpected_error_is_generic_500(unreachable_settings: Settings) -> None:
    app = create_app(settings=unreachable_settings)

    async def broken() -> None:
        raise RuntimeError(PRIVATE_TEXT)

    app.add_api_route("/broken", broken)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/broken")

    assert response.status_code == 500
    body = response.json()
    assert body == {
        "code": "internal_error",
        "detail": INTERNAL_ERROR_DETAIL,
        "request_id": response.headers[REQUEST_ID_HEADER],
    }
    assert PRIVATE_TEXT not in response.text
