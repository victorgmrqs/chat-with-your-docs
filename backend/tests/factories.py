"""Builders shared by tests. Importable module (tests never import from conftest)."""

import uuid
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.community.postgres import PostgresContainer

from app.adapters.parsers import DocumentParserAdapter, RecursiveTextSplitter
from app.application.answering import AnsweringLimits, AnswerQuestion
from app.application.ingestion import IngestionService
from app.application.ports import (
    ChatModelPort,
    DocumentRepository,
    EmbeddingPort,
    RetrieverPort,
)
from app.application.reranking import LLMReranker
from app.config import Settings
from app.domain.answers import RetrievedChunk
from app.domain.documents import Document, DocumentFormat, DocumentStatus
from app.domain.usage import PriceTable

BACKEND_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = BACKEND_DIR / "tests" / "fixtures" / "documents"
# application_name of the `isolated_engine` fixture, so a test can find its backend.
ISOLATED_APPLICATION_NAME = "cwyd-isolated-test"

# Size of the vector(N) column in migration 0001; fakes must produce vectors of this size.
EMBEDDING_DIMENSIONS: int = Settings.model_fields["embedding_dimensions"].default

VALID_SETTINGS: dict[str, str] = {
    "database_url": "postgresql+asyncpg://cwyd:cwyd@localhost:5432/cwyd",
    "chat_provider": "openai",
    "chat_model": "chat-model-x",
    "embedding_model": "embedding-model-x",
    "openai_api_key": "sk-test",
}

# The same settings as environment variables, as load_settings() reads them.
REQUIRED_ENV: dict[str, str] = {name.upper(): value for name, value in VALID_SETTINGS.items()}

# Builds a TestClient for one test's owner (`documents_client_for`, `chat_client_for`).
ClientFactory = Callable[..., TestClient]

# Fixture documents the chat tests upload before asking.
CHAT_DOCUMENTS = ("remote-work-policy.pdf", "expense-policy.pdf", "parental-leave-policy.md")


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


def make_retrieved_chunk(**overrides: Any) -> RetrievedChunk:
    """A retrieved chunk that passes the relevance gate; tests override what they are about."""
    chunk = RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        filename="expense-policy.pdf",
        page=2,
        heading=None,
        text="Coworking reimbursement is limited to US$ 250 per month per employee.",
        score=0.03,
        similarity=0.8,
        fts_matched=True,
    )
    return replace(chunk, **overrides)


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


ANSWERING_LIMITS = AnsweringLimits(
    question_max_chars=200,
    retrieval_candidates=20,
    retrieval_top_k=6,
    min_relevance=0.3,
    rerank_top_n=1,
    context_token_budget=3000,
)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def make_answering(
    retriever: RetrieverPort,
    embeddings: EmbeddingPort,
    chat: ChatModelPort,
    *,
    rerank: bool = False,
    prices: PriceTable | None = None,
    capture_content: bool = False,
) -> AnswerQuestion:
    """AnswerQuestion over the given fakes; the reranker, when on, uses the same chat model."""
    return AnswerQuestion(
        retriever,
        embeddings,
        chat,
        ANSWERING_LIMITS,
        reranker=LLMReranker(chat) if rerank else None,
        prices=prices,
        capture_content=capture_content,
    )


def make_ingestion(
    repository: DocumentRepository,
    embeddings: EmbeddingPort,
    max_upload_bytes: int = MAX_UPLOAD_BYTES,
) -> IngestionService:
    """Parser and splitter are the real, in-process adapters: deterministic, no I/O."""
    return IngestionService(
        repository,
        DocumentParserAdapter(),
        RecursiveTextSplitter(chunk_size=500, chunk_overlap=50),
        embeddings,
        max_upload_bytes=max_upload_bytes,
    )
