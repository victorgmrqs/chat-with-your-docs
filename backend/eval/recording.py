"""RetrieverPort decorator that keeps what the last search returned (questions run one by one)."""

import uuid
from collections.abc import Sequence

from app.application.ports import RetrieverPort
from app.domain.answers import RetrievedChunk


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
