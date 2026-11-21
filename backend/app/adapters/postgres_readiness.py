import asyncio

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeout
from sqlalchemy.ext.asyncio import AsyncEngine


class DatabaseUnavailable(Exception):
    """The database cannot be reached, refuses the connection or stops answering."""


class PostgresReadiness:
    """Checks that the database answers and has the pgvector extension installed."""

    def __init__(self, engine: AsyncEngine, timeout: float = 3.0) -> None:
        self._engine = engine
        self._timeout = timeout

    async def pgvector_version(self) -> str | None:
        """Installed pgvector version, or None when the extension is missing.

        Raises DatabaseUnavailable when connecting fails (refused, wrong credentials, missing
        database, server starting up, pool exhausted), when the connection drops during the
        query, or when the whole check exceeds the timeout. SQL and programming errors propagate.
        """
        try:
            async with asyncio.timeout(self._timeout):
                return await self._query_pgvector_version()
        except TimeoutError as exc:
            raise DatabaseUnavailable from exc

    async def _query_pgvector_version(self) -> str | None:
        connection = self._engine.connect()
        try:
            await connection.start()
        except (DBAPIError, OSError, PoolTimeout) as exc:
            raise DatabaseUnavailable from exc
        try:
            version = await connection.scalar(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            )
        except DBAPIError as exc:
            lost = isinstance(exc, InterfaceError | OperationalError) or exc.connection_invalidated
            if lost:
                raise DatabaseUnavailable from exc
            raise
        finally:
            await connection.close()
        return str(version) if version is not None else None
