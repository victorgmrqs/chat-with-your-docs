"""Builders shared by tests. Importable module (tests never import from conftest)."""

import uuid
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.community.postgres import PostgresContainer

from app.config import Settings
from app.domain.documents import Document, DocumentFormat, DocumentStatus

BACKEND_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = BACKEND_DIR / "tests" / "fixtures" / "documents"

# Size of the vector(N) column in migration 0001; fakes must produce vectors of this size.
EMBEDDING_DIMENSIONS: int = Settings.model_fields["embedding_dimensions"].default

VALID_SETTINGS: dict[str, str] = {
    "database_url": "postgresql+asyncpg://cwyd:cwyd@localhost:5432/cwyd",
    "chat_provider": "openai",
    "chat_model": "chat-model-x",
    "embedding_model": "embedding-model-x",
    "openai_api_key": "sk-test",
}


def make_settings(database_url: str, **overrides: Any) -> Settings:
    return Settings.model_validate({**VALID_SETTINGS, "database_url": database_url, **overrides})


def make_document(**overrides: Any) -> Document:
    """A valid Document in `indexing`; tests override only the fields they are about."""
    now = datetime.now(UTC)
    document = Document(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        filename="expense-policy.pdf",
        format=DocumentFormat.PDF,
        sha256="0" * 64,
        size_bytes=1024,
        status=DocumentStatus.INDEXING,
        failure_reason=None,
        chunk_count=0,
        created_at=now,
        updated_at=now,
    )
    return replace(document, **overrides)


def fixture_bytes(name: str) -> bytes:
    """Content of a generated fixture document (scripts/generate_fixtures.py)."""
    return (FIXTURES_DIR / name).read_bytes()


def alembic_config(database_url: str) -> Config:
    """Alembic config pointing at any database; env.py reads the URL from attributes."""
    config = Config(BACKEND_DIR / "alembic.ini")
    config.attributes["database_url"] = database_url
    return config


def psql(container: PostgresContainer, sql: str) -> str:
    """Run one statement with psql inside the container; unaligned, tuples-only output."""
    result = container.exec(["psql", "-U", container.username, "-d", container.dbname, "-tAc", sql])
    return result.output.decode().strip()


class StoredChunk(NamedTuple):
    filename: str
    owner_id: uuid.UUID
    chunk_index: int
    page: int | None
    heading: str | None
    text: str


async def stored_chunks(engine: AsyncEngine, document_id: uuid.UUID) -> list[StoredChunk]:
    """Database state of a document's chunks (joined with its file name), in order."""
    query = text(
        "SELECT d.filename, c.owner_id, c.chunk_index, c.page, c.heading, c.text "
        "FROM chunks c JOIN documents d ON d.id = c.document_id "
        "WHERE c.document_id = :id ORDER BY c.chunk_index"
    )
    async with engine.connect() as connection:
        result = await connection.execute(query, {"id": document_id})
        return [StoredChunk(*row) for row in result]
