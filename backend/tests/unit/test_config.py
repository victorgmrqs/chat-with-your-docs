import pytest

from app.config import ConfigurationError, load_settings
from tests.factories import VALID_SETTINGS

REQUIRED_ENV = {name.upper(): value for name, value in VALID_SETTINGS.items()}


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Start every test from a clean environment, whatever the shell exports."""
    for name in (*REQUIRED_ENV, "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.fixture
def valid_env(env: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Every required variable set; tests override or remove only the one they are about."""
    for name, value in REQUIRED_ENV.items():
        env.setenv(name, value)
    return env


@pytest.mark.usefixtures("valid_env")
def test_load_settings_success() -> None:
    settings = load_settings()

    assert settings.chat_provider == "openai"
    assert settings.chat_model == "chat-model-x"
    assert settings.openai_api_key.get_secret_value() == "sk-test"


def test_load_settings_missing_variables_names_each_one(env: pytest.MonkeyPatch) -> None:
    env.setenv("DATABASE_URL", REQUIRED_ENV["DATABASE_URL"])

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()

    message = str(exc_info.value)
    for name in ("CHAT_PROVIDER", "CHAT_MODEL", "EMBEDDING_MODEL", "OPENAI_API_KEY"):
        assert name in message
    assert "DATABASE_URL" not in message
    assert ".env.example" in message


def test_load_settings_empty_variable_counts_as_missing(valid_env: pytest.MonkeyPatch) -> None:
    valid_env.setenv("OPENAI_API_KEY", "")

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()

    assert "OPENAI_API_KEY" in str(exc_info.value)


def test_load_settings_rejects_a_sync_database_url(valid_env: pytest.MonkeyPatch) -> None:
    valid_env.setenv("DATABASE_URL", "postgresql://cwyd:cwyd@localhost:5432/cwyd")

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()

    message = str(exc_info.value)
    assert "DATABASE_URL" in message
    assert "postgresql+asyncpg://" in message


def test_load_settings_anthropic_provider_requires_its_key(valid_env: pytest.MonkeyPatch) -> None:
    valid_env.setenv("CHAT_PROVIDER", "anthropic")

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()

    assert "ANTHROPIC_API_KEY" in str(exc_info.value)


def test_load_settings_unknown_provider_lists_accepted_values(
    valid_env: pytest.MonkeyPatch,
) -> None:
    valid_env.setenv("CHAT_PROVIDER", "mistral")

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()

    message = str(exc_info.value)
    assert "CHAT_PROVIDER" in message
    assert "'openai'" in message
    assert "'anthropic'" in message
