"""Connections that turn an unreachable database into DatabaseUnavailable."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeout
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine


class DatabaseUnavailable(Exception):
    """The database cannot be reached, refuses the connection or stops answering."""


@asynccontextmanager
async def database_connection(
    engine: AsyncEngine, *, transaction: bool = False
) -> AsyncIterator[AsyncConnection]:
    """`engine.connect()` (or `begin()` with transaction=True) with failure translation.

    Raises DatabaseUnavailable when connecting fails (refused, wrong credentials, missing
    database, server starting up, pool exhausted) or the connection drops during a statement.
    SQL and programming errors (ProgrammingError, IntegrityError, ...) propagate untouched.
    """
    connection = engine.connect()
    try:
        await connection.start()
    except (DBAPIError, OSError, PoolTimeout) as exc:
        raise DatabaseUnavailable from exc
    try:
        if transaction:
            async with connection.begin():
                yield connection
        else:
            yield connection
    except DBAPIError as exc:
        if isinstance(exc, InterfaceError | OperationalError) or exc.connection_invalidated:
            raise DatabaseUnavailable from exc
        raise
    finally:
        await connection.close()
