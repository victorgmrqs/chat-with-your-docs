import asyncio

from sqlalchemy import TextClause, text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.adapters.postgres_connection import DatabaseUnavailable, database_connection

PGVECTOR_VERSION = text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")


class PostgresReadiness:
    """Checks that the database answers and has the pgvector extension installed."""

    def __init__(
        self, engine: AsyncEngine, timeout: float = 3.0, statement: TextClause = PGVECTOR_VERSION
    ) -> None:
        # `statement` is a test seam: tests swap in a stalled or invalid query.
        self._engine = engine
        self._timeout = timeout
        self._statement = statement

    async def pgvector_version(self) -> str | None:
        """Installed pgvector version, or None when the extension is missing.

        Raises DatabaseUnavailable when the database is unreachable (see database_connection)
        or the whole check exceeds the timeout. SQL and programming errors propagate.
        """
        try:
            async with asyncio.timeout(self._timeout), database_connection(self._engine) as conn:
                version = await conn.scalar(self._statement)
        except TimeoutError as exc:
            raise DatabaseUnavailable from exc
        return str(version) if version is not None else None
