import anthropic
from langchain_anthropic import ChatAnthropic
from pydantic import SecretStr

from app.adapters.langchain_chat import LangChainChatAdapter


class AnthropicChatAdapter(LangChainChatAdapter):
    """ChatModelPort over Anthropic; structured output through a forced tool call."""

    def __init__(
        self,
        model: str,
        api_key: SecretStr,
        *,
        max_tokens: int,
        timeout_seconds: float,
        max_retries: int,
        base_url: str | None = None,  # None: the provider's public endpoint
    ) -> None:
        client = ChatAnthropic(
            model=model,
            anthropic_api_key=api_key,
            max_tokens=max_tokens,
            default_request_timeout=timeout_seconds,
            max_retries=max_retries,
            anthropic_api_url=base_url,
            temperature=0,
        )
        super().__init__(
            "anthropic",
            model,
            client,
            method="function_calling",
            timeout_errors=(anthropic.APITimeoutError,),
            provider_errors=(anthropic.AnthropicError,),
        )
