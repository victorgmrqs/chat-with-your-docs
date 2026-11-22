import openai
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.adapters.langchain_chat import LangChainChatAdapter


class OpenAIChatAdapter(LangChainChatAdapter):
    """ChatModelPort over OpenAI; native JSON-schema structured output."""

    def __init__(
        self,
        model: str,
        api_key: SecretStr,
        *,
        max_tokens: int,
        timeout_seconds: float,
        max_retries: int,
        temperature: float | None = None,  # None: not sent, the provider's default applies
        base_url: str | None = None,  # None: the provider's public endpoint
    ) -> None:
        client = ChatOpenAI(
            model_name=model,
            openai_api_key=api_key,
            max_tokens=max_tokens,
            request_timeout=timeout_seconds,
            max_retries=max_retries,
            openai_api_base=base_url,
            temperature=temperature,
        )
        super().__init__(
            "openai",
            model,
            client,
            method="json_schema",
            timeout_errors=(openai.APITimeoutError,),
            provider_errors=(openai.OpenAIError,),
        )
