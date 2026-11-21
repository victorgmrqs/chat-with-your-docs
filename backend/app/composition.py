from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.adapters.postgres_readiness import PostgresReadiness
from app.config import Settings


@dataclass(frozen=True, slots=True)
class Container:
    """Concrete dependencies built once at startup and shared by every request."""

    settings: Settings
    engine: AsyncEngine
    readiness: PostgresReadiness


def build_container(settings: Settings) -> Container:
    engine = create_async_engine(str(settings.database_url), pool_pre_ping=True)
    readiness = PostgresReadiness(engine)
    return Container(settings=settings, engine=engine, readiness=readiness)
