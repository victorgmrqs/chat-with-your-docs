from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.adapters.openai_embeddings import OpenAIEmbeddingAdapter
from app.adapters.parsers import DocumentParserAdapter, RecursiveTextSplitter
from app.adapters.postgres_documents import PostgresDocumentRepository
from app.adapters.postgres_readiness import PostgresReadiness
from app.application.ingestion import IngestionService
from app.application.ports import EmbeddingPort
from app.config import Settings


@dataclass(frozen=True, slots=True)
class Container:
    """Concrete dependencies built once at startup and shared by every request."""

    settings: Settings
    engine: AsyncEngine
    readiness: PostgresReadiness
    ingestion: IngestionService


def build_container(settings: Settings, embeddings: EmbeddingPort | None = None) -> Container:
    """`embeddings` replaces the OpenAI adapter in tests (declared fakes, no network)."""
    # hide_parameters: driver errors must not echo bound values (chunk text) into logs.
    engine = create_async_engine(
        str(settings.database_url), pool_pre_ping=True, hide_parameters=True
    )
    ingestion = IngestionService(
        PostgresDocumentRepository(engine),
        DocumentParserAdapter(),
        RecursiveTextSplitter(settings.chunk_size, settings.chunk_overlap),
        embeddings
        or OpenAIEmbeddingAdapter(
            settings.embedding_model, settings.openai_api_key, settings.embedding_dimensions
        ),
        max_upload_bytes=settings.max_upload_bytes,
    )
    return Container(
        settings=settings,
        engine=engine,
        readiness=PostgresReadiness(engine),
        ingestion=ingestion,
    )
