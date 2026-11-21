from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health
from app.composition import build_container
from app.config import Settings, load_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = build_container(settings or load_settings())
        app.state.container = container
        yield
        await container.engine.dispose()

    app = FastAPI(title="Chat With Your Docs API", lifespan=lifespan)
    app.include_router(health.router)
    return app


app = create_app()
