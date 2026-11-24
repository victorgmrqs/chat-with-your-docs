from collections.abc import Iterator, Sequence

import openai
from pydantic import SecretStr

from app.application.ports import EmbeddingMisconfigured, EmbeddingUnavailable, Generation
from app.domain.usage import TokenUsage

# DOM-25: the key or the model is wrong; retrying will not help until the operator fixes it.
_MISCONFIGURED = (openai.AuthenticationError, openai.PermissionDeniedError, openai.NotFoundError)

# One request stays under the provider's per-request input limits (2048 inputs, 300k tokens):
# at most this many texts, and at most this many characters (about 100k tokens even for text
# that tokenizes at one token per character).
MAX_BATCH_TEXTS = 256
MAX_BATCH_CHARS = 100_000


class OpenAIEmbeddingAdapter:
    """EmbeddingPort over the OpenAI SDK (`embeddings.create`), called directly because it
    returns the token usage LangChain's OpenAIEmbeddings drops (DOM-24, CWYD-28).

    The client retries transient errors (429, 5xx, timeouts) with exponential backoff; what still
    fails becomes EmbeddingUnavailable (DOM-03). A rejected key or unknown model becomes
    EmbeddingMisconfigured (DOM-25). Errors carry the exception type only.
    """

    def __init__(
        self,
        model: str,
        api_key: SecretStr,
        dimensions: int,
        *,
        max_retries: int = 3,
        timeout_seconds: float = 30.0,
        base_url: str | None = None,
        max_batch_texts: int = MAX_BATCH_TEXTS,
        max_batch_chars: int = MAX_BATCH_CHARS,
    ) -> None:
        self._model = model
        self._dimensions = dimensions
        self._max_batch_texts = max_batch_texts
        self._max_batch_chars = max_batch_chars
        self._client = openai.AsyncOpenAI(
            api_key=api_key.get_secret_value(),
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

    async def embed_documents(self, texts: Sequence[str]) -> Generation[list[list[float]]]:
        vectors: list[list[float]] = []
        usage: list[TokenUsage | None] = []
        try:
            for batch in _batches(texts, self._max_batch_texts, self._max_batch_chars):
                response = await self._client.embeddings.create(
                    model=self._model,
                    input=batch,
                    dimensions=self._dimensions,
                    encoding_format="float",
                )
                if len(response.data) != len(batch):  # a broken reply, not a partial result
                    raise EmbeddingUnavailable("EmbeddingCountMismatch")
                vectors.extend(item.embedding for item in sorted(response.data, key=_index))
                usage.append(
                    TokenUsage(response.model, response.usage.prompt_tokens, 0)
                    if response.usage is not None
                    else None
                )
        except _MISCONFIGURED as exc:
            # Exception type only: provider messages may echo request content.
            raise EmbeddingMisconfigured(type(exc).__name__) from exc
        except openai.OpenAIError as exc:
            raise EmbeddingUnavailable(type(exc).__name__) from exc
        return Generation(vectors, _merged(usage))


def _index(item: openai.types.Embedding) -> int:
    return item.index


def _batches(texts: Sequence[str], max_texts: int, max_chars: int) -> Iterator[list[str]]:
    """Consecutive batches in input order; a single text longer than `max_chars` goes alone."""
    batch: list[str] = []
    chars = 0
    for text in texts:
        if batch and (len(batch) == max_texts or chars + len(text) > max_chars):
            yield batch
            batch, chars = [], 0
        batch.append(text)
        chars += len(text)
    if batch:
        yield batch


def _merged(usage: Sequence[TokenUsage | None]) -> tuple[TokenUsage, ...]:
    """One entry per call of embed_documents, however many requests it took. If any request
    reported no usage the total is unknown, so nothing is reported (DOM-24: never too low)."""
    known = [u for u in usage if u is not None]
    if not known or len(known) != len(usage):
        return ()
    return (TokenUsage(known[0].model, sum(u.input_tokens for u in known), 0),)
