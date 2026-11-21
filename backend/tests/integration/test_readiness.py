from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from testcontainers.community.postgres import PostgresContainer

from app.config import Settings
from app.main import create_app

pytestmark = pytest.mark.integration


def test_ready_reports_pgvector_version(
    postgres: PostgresContainer, settings_for: Callable[[str], Settings]
) -> None:
    settings = settings_for(postgres.get_connection_url())

    with TestClient(create_app(settings=settings)) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["pgvector"]


def test_ready_is_unavailable_without_the_vector_extension(
    postgres: PostgresContainer, settings_for: Callable[[str], Settings]
) -> None:
    url = make_url(postgres.get_connection_url()).set(database="without_vector")

    with TestClient(create_app(settings=settings_for(url.render_as_string(False)))) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "pgvector extension missing"}


def test_ready_is_unavailable_with_wrong_credentials(
    postgres: PostgresContainer, settings_for: Callable[[str], Settings]
) -> None:
    url = make_url(postgres.get_connection_url()).set(password="not-the-password")  # noqa: S106  # deliberately wrong

    with TestClient(create_app(settings=settings_for(url.render_as_string(False)))) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}


def test_ready_is_unavailable_when_the_database_is_down(unreachable_settings: Settings) -> None:
    with TestClient(create_app(settings=unreachable_settings)) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}
