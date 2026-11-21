"""Alembic environment: async engine, hand-written migrations (no ORM metadata)."""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config


def _database_url() -> str:
    """Tests inject the URL via config.attributes; otherwise only DATABASE_URL is needed."""
    url = config.attributes.get("database_url") or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required to run migrations (see .env.example).")
    return str(url)


# configparser treats "%" as interpolation: escape it (URL-encoded passwords).
config.set_main_option("sqlalchemy.url", _database_url().replace("%", "%%"))

if config.config_file_name is not None:
    # Keep loggers configured by the host process (pytest, uvicorn) enabled.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = None  # migrations are hand-written (SQL Core + text(), no ORM models)


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a database connection (`alembic upgrade head --sql`)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    # Runs its own event loop: call from synchronous code only (CLI, sync fixtures).
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
