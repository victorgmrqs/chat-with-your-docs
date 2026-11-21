from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.image import DockerImage

from app.adapters.postgres_documents import PostgresDocumentRepository
from app.config import Settings
from tests.factories import alembic_config, make_settings, psql

DB_IMAGE_DIR = Path(__file__).resolve().parents[2] / "db"


@pytest.fixture
def unreachable_settings() -> Settings:
    """Points at a closed port: the engine is created but every connection fails."""
    return make_settings("postgresql+asyncpg://cwyd:cwyd@127.0.0.1:1/cwyd")


@pytest.fixture
def settings_for() -> Callable[[str], Settings]:
    """Factory: Settings pointing at any database URL (e.g. a testcontainers instance)."""
    return make_settings


@pytest.fixture(scope="session")
def postgres() -> Iterator[PostgresContainer]:
    """PostgreSQL built from db/Dockerfile (runtime target), migrated to head.

    Synchronous on purpose: migrations/env.py runs its own event loop (asyncio.run).
    """
    with (
        DockerImage(path=DB_IMAGE_DIR, tag="cwyd-db:test", target="runtime") as image,
        PostgresContainer(str(image), driver="asyncpg") as container,
    ):
        psql(container, "CREATE DATABASE without_vector")
        command.upgrade(alembic_config(container.get_connection_url()), "head")
        yield container


@pytest.fixture(scope="session")
async def engine(postgres: PostgresContainer) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(postgres.get_connection_url())
    yield engine
    await engine.dispose()


@pytest.fixture
def repository(engine: AsyncEngine) -> PostgresDocumentRepository:
    return PostgresDocumentRepository(engine)
