import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import chat, documents, health
from app.api.errors import register_error_handlers
from app.application.ports import ChatModelPort, EmbeddingPort
from app.composition import Container, build_container
from app.config import Settings, load_settings

logger = logging.getLogger(__name__)

RECOVERY_TIMEOUT_SECONDS = 10


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
        container = build_container(settings or load_settings(), embeddings, chat_model)
        app.state.container = container
        await _recover_interrupted_indexing(container)
        yield
        await container.engine.dispose()

    app = FastAPI(title="Chat With Your Docs API", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(chat.router)
    return app


app = create_app()
