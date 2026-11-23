import asyncio
import logging
from collections.abc import AsyncIterator, MutableMapping
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from app.adapters.telemetry import configure_tracing
from app.api import chat, documents, health
from app.api.errors import register_error_handlers
from app.api.request_id import add_request_id
from app.application.ports import ChatModelPort, EmbeddingPort
from app.composition import Container, build_container
from app.config import Settings, load_settings

logger = logging.getLogger(__name__)

RECOVERY_TIMEOUT_SECONDS = 10


def _is_health_probe(scope: MutableMapping[str, Any]) -> bool:
    """Compose and k8s probe these every few seconds: a trace each would bury the real ones."""
    return str(scope.get("path", "")).startswith("/health")


async def _recover_interrupted_indexing(container: Container) -> None:
    """DOM-03 at startup. Best effort: with the database down the API still starts and
    /health/ready reports it; the next start retries."""
    try:
        async with asyncio.timeout(RECOVERY_TIMEOUT_SECONDS):
            recovered = await container.ingestion.recover_interrupted()
    except Exception as exc:
        error_type = type(exc).__name__
        logger.warning(
            "Indexing recovery skipped: %s", error_type, extra={"error_type": error_type}
        )
        return
    if recovered:
        logger.info("Interrupted indexing marked as failed: %d", recovered)


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
        yield
        await container.engine.dispose()
        if tracer_provider is not None:
            # Flushes the spans still batched; blocking (up to the export timeout when the
            # collector is gone), so off the event loop.
            await asyncio.to_thread(tracer_provider.shutdown)

    # FastAPI's native telemetry adds the HTTP server span (the trace root, route and status)
    # and operation spans around our pipeline spans whenever a tracer provider is set. It
    # records exceptions by type only, like ours (DOM-22).
    app = FastAPI(
        title="Chat With Your Docs API",
        lifespan=lifespan,
        telemetry={"exclude": _is_health_probe},
    )
    app.middleware("http")(add_request_id)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(chat.router)
    return app


app = create_app()
