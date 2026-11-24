import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, MutableMapping
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from app.adapters.telemetry import configure_tracing
from app.api import chat, documents, health
from app.api.body_limit import BodySizeLimit
from app.api.errors import register_error_handlers
from app.api.forwarded_prefix import ForwardedPrefix
from app.api.request_id import add_request_id
from app.application.ports import ChatModelPort, EmbeddingPort
from app.composition import Container, build_container
from app.config import HttpSettings, Settings, load_settings
from app.domain.documents import EmbeddingDimensionMismatch

logger = logging.getLogger(__name__)

RECOVERY_TIMEOUT_SECONDS = 10


def _is_health_probe(scope: MutableMapping[str, Any]) -> bool:
    """Compose and k8s probe these every few seconds: a trace each would bury the real ones."""
    path, root = str(scope.get("path", "")), str(scope.get("root_path", ""))
    return path.removeprefix(root).startswith("/health")  # behind the /api prefix too (CWYD-20)


async def _best_effort[T](label: str, step: Awaitable[T]) -> T | None:
    """A startup step that never stops the API: with the database down it still starts,
    /health/ready reports it and the next start retries. None when skipped."""
    try:
        async with asyncio.timeout(RECOVERY_TIMEOUT_SECONDS):
            return await step
    except Exception as exc:
        error_type = type(exc).__name__
        logger.warning("%s skipped: %s", label, error_type, extra={"error_type": error_type})
        return None


async def _recover_interrupted_indexing(container: Container) -> None:
    """DOM-03 at startup."""
    recovered = await _best_effort("Indexing recovery", container.ingestion.recover_interrupted())
    if recovered:
        logger.info("Interrupted indexing marked as failed: %d", recovered)


async def _check_embedding_dimensions(container: Container) -> None:
    """DOM-26 at startup: a mismatch is logged once. The API still starts; readiness and
    uploads report it."""

    async def check() -> None:
        try:
            await container.ingestion.check_embedding_dimensions()
        except EmbeddingDimensionMismatch as exc:
            logger.error(
                "Embedding dimension mismatch: EMBEDDING_DIMENSIONS=%d, chunks.embedding=%d",
                exc.configured,
                exc.stored,
                extra={"configured_dimensions": exc.configured, "stored_dimensions": exc.stored},
            )

    await _best_effort("Embedding dimension check", check())


def create_app(
    settings: Settings | None = None,
    embeddings: EmbeddingPort | None = None,
    chat_model: ChatModelPort | None = None,
) -> FastAPI:
    """`embeddings` and `chat_model` override the provider adapters (tests use fakes)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        loaded = settings or load_settings()
        tracer_provider = configure_tracing(loaded)  # None with OTEL_TRACES_EXPORTER=none
        container = build_container(loaded, embeddings, chat_model)
        app.state.container = container
        await _recover_interrupted_indexing(container)
        await _check_embedding_dimensions(container)
        yield
        await container.engine.dispose()
        if tracer_provider is not None:
            # Flushes the spans still batched; blocking (up to the export timeout when the
            # collector is gone), so off the event loop.
            await asyncio.to_thread(tracer_provider.shutdown)

    http = settings or HttpSettings()
    docs = http.api_docs_enabled

    # FastAPI's native telemetry adds the HTTP server span (the trace root, route and status)
    # and operation spans around our pipeline spans whenever a tracer provider is set. Spans
    # record exceptions by type only, like ours; its log signal is off because those records
    # carry exception messages and stack traces (DOM-22, CWYD-27).
    app = FastAPI(
        title="Chat With Your Docs API",
        lifespan=lifespan,
        # None also drops /docs and /redoc; app.openapi() still builds the schema for the export.
        openapi_url="/openapi.json" if docs else None,
        telemetry={"exclude": _is_health_probe, "logs": False},
    )

    def loaded_settings() -> Settings | None:
        container: Container | None = getattr(app.state, "container", None)
        return container.settings if container is not None else None

    # Added first, so it runs inside the request-id middleware and its 413 carries the id.
    app.add_middleware(BodySizeLimit, settings=loaded_settings)
    app.middleware("http")(add_request_id)
    # Outermost: everything inside, the docs included, sees the root path set.
    app.add_middleware(ForwardedPrefix, prefix=http.api_root_path)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(chat.router)
    return app


app = create_app()
