"""DOM-13: the chat provider comes from configuration only. Building adapters is offline."""

import pytest

from app.adapters.anthropic_chat import AnthropicChatAdapter
from app.adapters.openai_chat import OpenAIChatAdapter
from app.composition import build_chat_model
from tests.factories import make_settings

DATABASE_URL = "postgresql+asyncpg://cwyd:cwyd@localhost:5432/cwyd"


@pytest.mark.parametrize(
    ("provider", "model", "adapter_type"),
    [
        ("openai", "gpt-configured", OpenAIChatAdapter),
        ("anthropic", "claude-configured", AnthropicChatAdapter),
    ],
)
def test_build_chat_model_selects_adapter_by_provider(
    provider: str, model: str, adapter_type: type
) -> None:
    settings = make_settings(
        DATABASE_URL,
        chat_provider=provider,
        chat_model=model,
        openai_api_key="sk-openai-key",
        anthropic_api_key="sk-anthropic-key",
    )

    adapter = build_chat_model(settings)

    assert isinstance(adapter, adapter_type)
    assert (adapter.provider, adapter.model) == (provider, model)


def test_build_chat_model_anthropic_uses_anthropic_key() -> None:
    settings = make_settings(
        DATABASE_URL,
        chat_provider="anthropic",
        openai_api_key="sk-openai-key",
        anthropic_api_key="sk-anthropic-key",
    )

    adapter = build_chat_model(settings)

    assert isinstance(adapter, AnthropicChatAdapter)
    assert adapter._client.anthropic_api_key.get_secret_value() == "sk-anthropic-key"  # type: ignore[attr-defined]  # LangChain client field, checked on purpose


def test_build_chat_model_openai_uses_openai_key() -> None:
    settings = make_settings(
        DATABASE_URL,
        chat_provider="openai",
        openai_api_key="sk-openai-key",
        anthropic_api_key="sk-anthropic-key",
    )

    adapter = build_chat_model(settings)

    assert isinstance(adapter, OpenAIChatAdapter)
    assert adapter._client.openai_api_key.get_secret_value() == "sk-openai-key"  # type: ignore[attr-defined]  # LangChain client field, checked on purpose


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_build_chat_model_temperature_unset_by_default(provider: str) -> None:
    settings = make_settings(DATABASE_URL, chat_provider=provider, anthropic_api_key="sk-ant")

    adapter = build_chat_model(settings)

    assert adapter._client.temperature is None  # type: ignore[attr-defined]  # LangChain client, checked on purpose


def test_build_chat_model_applies_configured_temperature() -> None:
    settings = make_settings(DATABASE_URL, chat_temperature=0.2)

    adapter = build_chat_model(settings)

    assert adapter._client.temperature == 0.2  # type: ignore[attr-defined]  # LangChain client, checked on purpose


def test_build_chat_model_applies_configured_limits() -> None:
    settings = make_settings(
        DATABASE_URL, answer_max_tokens=321, chat_timeout_seconds=7, chat_max_retries=1
    )

    adapter = build_chat_model(settings)

    client = adapter._client  # type: ignore[attr-defined]  # LangChain client, checked on purpose
    assert (client.max_tokens, client.request_timeout, client.max_retries) == (321, 7, 1)
