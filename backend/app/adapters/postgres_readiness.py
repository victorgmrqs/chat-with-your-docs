import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.adapters.postgres_connection import DatabaseUnavailable, database_connection


class PostgresReadiness:
    """Checks that the database answers and has the pgvector extension installed."""

    def __init__(self, engine: AsyncEngine, timeout: float = 3.0) -> None:
        self._engine = engine
        self._timeout = timeout

    async def pgvector_version(self) -> str | None:
        """Installed pgvector version, or None when the extension is missing.

        Raises DatabaseUnavailable when the database is unreachable (see database_connection)
        or the whole check exceeds the timeout. SQL and programming errors propagate.
        """
        try:
            async with asyncio.timeout(self._timeout), database_connection(self._engine) as conn:
                version = await conn.scalar(
                    text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
                )
        except TimeoutError as exc:
            raise DatabaseUnavailable from exc
        return str(version) if version is not None else None
