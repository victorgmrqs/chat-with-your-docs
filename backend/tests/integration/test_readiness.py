from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.image import DockerImage

from app.config import Settings
from app.main import create_app

pytestmark = pytest.mark.integration

DB_IMAGE_DIR = Path(__file__).resolve().parents[3] / "db"


@pytest.fixture(scope="session")
def postgres() -> Iterator[PostgresContainer]:
    """PostgreSQL built from db/Dockerfile (runtime target): same init scripts as Compose."""
    with (
        DockerImage(path=DB_IMAGE_DIR, tag="cwyd-db:test", target="runtime") as image,
        PostgresContainer(str(image), driver="asyncpg") as container,
    ):
        container.exec(
            [
                "psql",
                "-U",
                container.username,
                "-d",
                container.dbname,
                "-c",
                "CREATE DATABASE without_vector",
            ]
        )
        yield container


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
