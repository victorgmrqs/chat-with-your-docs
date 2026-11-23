"""Port decorators that keep what the current question used (questions run one by one)."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from app.application.ports import EmbeddingPort, Generation, RetrieverPort
from app.domain.answers import RetrievedChunk
from app.domain.usage import TokenUsage


class RecordingRetriever:
    def __init__(self, inner: RetrieverPort) -> None:
        self._inner = inner
        self.last: list[RetrievedChunk] = []

    def reset(self) -> None:
        self.last = []

    async def has_ready_documents(self, owner_id: uuid.UUID) -> bool:
        return await self._inner.has_ready_documents(owner_id)

    async def search(
        self,
        owner_id: uuid.UUID,
        query_text: str,
        query_embedding: Sequence[float],
        *,
        candidates: int,
        limit: int,
    ) -> list[RetrievedChunk]:
        self.last = await self._inner.search(
            owner_id, query_text, query_embedding, candidates=candidates, limit=limit
        )
        return self.last


class RecordingEmbeddings:
    """Keeps the embedding usage since the last reset (DOM-24). The chat usage comes from
    LangChain's callback; embeddings call the provider SDK directly, so they are recorded here."""

    def __init__(self, inner: EmbeddingPort) -> None:
        self._inner = inner
        self.usage: list[TokenUsage] = []

    def reset(self) -> None:
        self.usage = []

    async def embed_documents(self, texts: Sequence[str]) -> Generation[list[list[float]]]:
        generation = await self._inner.embed_documents(texts)
        self.usage.extend(generation.usage)
        return generation


@dataclass(frozen=True, slots=True)
class Recorders:
    retrieval: RecordingRetriever
    embeddings: RecordingEmbeddings

    def reset(self) -> None:
        self.retrieval.reset()
        self.embeddings.reset()
