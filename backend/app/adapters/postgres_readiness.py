import asyncio

from sqlalchemy import TextClause, text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.adapters.postgres_connection import DatabaseUnavailable, database_connection

PGVECTOR_VERSION = text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")

# pgvector stores a `vector(n)` column's dimension as its type modifier (-1 when unspecified).
EMBEDDING_DIMENSIONS = text(
    "SELECT atttypmod FROM pg_attribute"
    " WHERE attrelid = to_regclass('chunks') AND attname = 'embedding' AND NOT attisdropped"
)


class PostgresReadiness:
    """Checks that the database answers and has the pgvector extension installed, and reads
    the embedding column's dimension (VectorSchemaPort, DOM-26)."""

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
        version = await self._scalar(self._statement)
        return str(version) if version is not None else None

    async def embedding_dimensions(self) -> int | None:
        """Dimension of `chunks.embedding`; None when the column is missing or unsized.

        Raises like pgvector_version.
        """
        dimensions = await self._scalar(EMBEDDING_DIMENSIONS)
        return dimensions if isinstance(dimensions, int) and dimensions > 0 else None

    async def _scalar(self, statement: TextClause) -> object:
        try:
            async with asyncio.timeout(self._timeout), database_connection(self._engine) as conn:
                return await conn.scalar(statement)
        except TimeoutError as exc:
            raise DatabaseUnavailable from exc
