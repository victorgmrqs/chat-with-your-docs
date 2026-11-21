from collections.abc import Sequence

import openai
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from app.application.ports import EmbeddingUnavailable


class OpenAIEmbeddingAdapter:
    """EmbeddingPort over OpenAI. The client retries transient errors (429, 5xx, timeouts)
    with exponential backoff; what still fails becomes EmbeddingUnavailable (DOM-03)."""

    def __init__(
        self,
        model: str,
        api_key: SecretStr,
        dimensions: int,
        *,
        max_retries: int = 3,
        timeout_seconds: float = 30.0,
        base_url: str | None = None,
    ) -> None:
        self._client = OpenAIEmbeddings(
            model=model,
            openai_api_key=api_key,
            dimensions=dimensions,
            max_retries=max_retries,
            request_timeout=timeout_seconds,
            openai_api_base=base_url,
            # Chunks (CHUNK_SIZE characters) are far below the model context: skip tiktoken.
            check_embedding_ctx_length=False,
        )

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            return await self._client.aembed_documents(list(texts))
        except openai.OpenAIError as exc:
            # Exception type only: provider messages may echo request content.
            raise EmbeddingUnavailable(type(exc).__name__) from exc
