import pytest
from alembic import command
from testcontainers.community.postgres import PostgresContainer

from tests.factories import alembic_config, psql

pytestmark = pytest.mark.integration


def _public_tables(postgres: PostgresContainer) -> str:
    return psql(
        postgres,
        "SELECT string_agg(tablename, ',' ORDER BY tablename) "
        "FROM pg_tables WHERE schemaname = 'public'",
    )


def test_migrations_downgrade_and_upgrade_roundtrip(postgres: PostgresContainer) -> None:
    config = alembic_config(postgres.get_connection_url())

    command.downgrade(config, "base")
    after_downgrade = _public_tables(postgres)
    command.upgrade(config, "head")

    assert after_downgrade == "alembic_version"
    assert _public_tables(postgres) == "alembic_version,chunks,documents"
