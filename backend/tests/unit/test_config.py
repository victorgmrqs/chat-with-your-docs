import pytest
from pydantic import ValidationError

from app.config import ConfigurationError, HttpSettings, load_settings
from tests.factories import REQUIRED_ENV


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


@pytest.mark.usefixtures("valid_env")
def test_load_settings_rejects_overlap_not_smaller_than_chunk_size(
    env: pytest.MonkeyPatch,
) -> None:
    env.setenv("CHUNK_SIZE", "100")
    env.setenv("CHUNK_OVERLAP", "100")

    with pytest.raises(ConfigurationError, match="CHUNK_OVERLAP must be smaller than CHUNK_SIZE"):
        load_settings()


def test_load_settings_answering_defaults(valid_env: pytest.MonkeyPatch) -> None:
    settings = load_settings()

    assert (settings.rerank_enabled, settings.min_relevance, settings.retrieval_top_k) == (
        False,
        0.30,
        6,
    )


def test_load_settings_rejects_top_k_beyond_candidates(valid_env: pytest.MonkeyPatch) -> None:
    valid_env.setenv("RETRIEVAL_CANDIDATES", "2")
    valid_env.setenv("RETRIEVAL_TOP_K", "5")

    with pytest.raises(ConfigurationError, match="RETRIEVAL_TOP_K cannot exceed"):
        load_settings()


def test_load_settings_rejects_min_relevance_above_one(valid_env: pytest.MonkeyPatch) -> None:
    valid_env.setenv("MIN_RELEVANCE", "1.5")

    with pytest.raises(ConfigurationError, match="MIN_RELEVANCE"):
        load_settings()


@pytest.mark.parametrize("value", ["api", "/api/", "/", "/a b", "/api//docs"])
def test_api_root_path_must_be_an_absolute_path_without_trailing_slash(value: str) -> None:
    """CWYD-20: compared verbatim with X-Forwarded-Prefix; a malformed value never matches."""
    with pytest.raises(ValidationError):
        HttpSettings(api_root_path=value)
