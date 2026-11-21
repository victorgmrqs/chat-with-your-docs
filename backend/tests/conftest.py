from collections.abc import Callable

import pytest

from app.config import Settings


def make_settings(database_url: str) -> Settings:
    return Settings.model_validate(
        {
            "database_url": database_url,
            "chat_provider": "openai",
            "chat_model": "chat-model-x",
            "embedding_model": "embedding-model-x",
            "openai_api_key": "sk-test",
        }
    )


@pytest.fixture
def unreachable_settings() -> Settings:
    """Points at a closed port: the engine is created but every connection fails."""
    return make_settings("postgresql+asyncpg://cwyd:cwyd@127.0.0.1:1/cwyd")


@pytest.fixture
def settings_for() -> Callable[[str], Settings]:
    """Factory: Settings pointing at any database URL (e.g. a testcontainers instance)."""
    return make_settings
