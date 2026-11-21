from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


class PostgresReadiness:
    """Checks that the database answers and has the pgvector extension installed."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def pgvector_version(self) -> str | None:
        async with self._engine.connect() as connection:
            version = await connection.scalar(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            )
        return str(version) if version is not None else None
