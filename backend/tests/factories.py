"""Builders shared by tests. Importable module (tests never import from conftest)."""

from app.config import Settings

VALID_SETTINGS: dict[str, str] = {
    "database_url": "postgresql+asyncpg://cwyd:cwyd@localhost:5432/cwyd",
    "chat_provider": "openai",
    "chat_model": "chat-model-x",
    "embedding_model": "embedding-model-x",
    "openai_api_key": "sk-test",
}


def make_settings(database_url: str) -> Settings:
    return Settings.model_validate({**VALID_SETTINGS, "database_url": database_url})
