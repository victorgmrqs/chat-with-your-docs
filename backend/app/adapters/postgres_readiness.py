import asyncio

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine


class DatabaseUnavailable(Exception):
    """The database cannot be reached or refuses the connection."""


class PostgresReadiness:
    """Checks that the database answers and has the pgvector extension installed."""

    def __init__(self, engine: AsyncEngine, connect_timeout: float = 3.0) -> None:
        self._engine = engine
        self._connect_timeout = connect_timeout

    async def pgvector_version(self) -> str | None:
        """Installed pgvector version, or None when the extension is missing.

        Any failure while connecting (refused, timeout, wrong credentials, missing database,
        server starting up) raises DatabaseUnavailable. Errors from the query itself propagate.
        """
        connection = self._engine.connect()
        try:
            async with asyncio.timeout(self._connect_timeout):
                await connection.start()
        except (DBAPIError, OSError, TimeoutError) as exc:
            raise DatabaseUnavailable from exc
        try:
            version = await connection.scalar(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            )
        finally:
            await connection.close()
        return str(version) if version is not None else None
