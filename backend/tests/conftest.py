from collections.abc import Callable

import pytest

from app.config import Settings
from tests.factories import make_settings


@pytest.fixture
def unreachable_settings() -> Settings:
    """Points at a closed port: the engine is created but every connection fails."""
    return make_settings("postgresql+asyncpg://cwyd:cwyd@127.0.0.1:1/cwyd")


@pytest.fixture
def settings_for() -> Callable[[str], Settings]:
    """Factory: Settings pointing at any database URL (e.g. a testcontainers instance)."""
    return make_settings
