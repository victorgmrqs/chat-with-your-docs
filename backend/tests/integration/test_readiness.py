import asyncio
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.community.postgres import PostgresContainer

from app.adapters.postgres_connection import DatabaseUnavailable
from app.adapters.postgres_readiness import PostgresReadiness
from app.config import Settings
from app.main import create_app
from tests.factories import ISOLATED_APPLICATION_NAME

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


# A sleep far longer than any timeout used here: the outcome never depends on timing.
STALLED = text("SELECT pg_sleep(60)::text")


async def test_pgvector_version_times_out_as_database_unavailable(
    isolated_engine: AsyncEngine,
) -> None:
    readiness = PostgresReadiness(isolated_engine, timeout=0.2, statement=STALLED)

    with pytest.raises(DatabaseUnavailable):
        await readiness.pgvector_version()


async def _terminate_stalled_backend(engine: AsyncEngine) -> None:
    """Wait until the isolated engine's query is running, then kill its backend."""
    find = text(
        "SELECT pid FROM pg_stat_activity"
        " WHERE application_name = :name AND state = 'active' AND query LIKE '%pg_sleep%'"
    )
    for _ in range(200):  # up to ~10 s for the query to start
        # A new transaction per poll: pg_stat_activity is a snapshot within one transaction.
        async with engine.connect() as conn:
            pid = await conn.scalar(find, {"name": ISOLATED_APPLICATION_NAME})
            if pid is not None:
                await conn.execute(text("SELECT pg_terminate_backend(:pid)"), {"pid": pid})
                return
        await asyncio.sleep(0.05)
    pytest.fail("the stalled readiness query never started")


async def test_pgvector_version_lost_connection_is_database_unavailable(
    isolated_engine: AsyncEngine, engine: AsyncEngine
) -> None:
    readiness = PostgresReadiness(isolated_engine, timeout=30, statement=STALLED)

    check = asyncio.create_task(readiness.pgvector_version())
    await _terminate_stalled_backend(engine)

    with pytest.raises(DatabaseUnavailable):
        await check


async def test_pgvector_version_propagates_programming_errors(
    isolated_engine: AsyncEngine,
) -> None:
    readiness = PostgresReadiness(
        isolated_engine, statement=text("SELECT extversion FROM no_such_table")
    )

    with pytest.raises(ProgrammingError):
        await readiness.pgvector_version()
