"""Declared fakes implementing the application ports. No network calls in tests."""

import hashlib
import uuid
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from app.application.ports import EmbeddingUnavailable
from app.domain.documents import Chunk, Document, DocumentStatus, FailureReason


class FakeEmbeddings:
    """Deterministic vectors derived from the text hash: same text, same vector."""

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        seed = hashlib.sha256(text.encode()).digest()
        return [seed[i % len(seed)] / 255 for i in range(self.dimensions)]


class FailingEmbeddings:
    """Provider still failing after the adapter's retries (transient failure)."""

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        raise EmbeddingUnavailable("provider unavailable")


class InMemoryDocumentRepository:
    """DocumentRepository kept in dicts; same contract as the Postgres adapter."""

    def __init__(self) -> None:
        self.documents: dict[uuid.UUID, Document] = {}
        self.chunks: dict[uuid.UUID, list[Chunk]] = {}

    async def create_or_get(self, document: Document) -> tuple[Document, bool]:
        for existing in self.documents.values():
            if existing.owner_id == document.owner_id and existing.sha256 == document.sha256:
                return existing, False
        self.documents[document.id] = document
        return document, True

    async def get(self, owner_id: uuid.UUID, document_id: uuid.UUID) -> Document | None:
        document = self.documents.get(document_id)
        return document if document is not None and document.owner_id == owner_id else None

    async def list_for_owner(self, owner_id: uuid.UUID) -> list[Document]:
        owned = [d for d in self.documents.values() if d.owner_id == owner_id]
        return sorted(owned, key=lambda d: d.created_at, reverse=True)

    async def mark_indexing(self, document_id: uuid.UUID) -> Document | None:
        document = self.documents.get(document_id)
        if document is None or not document.can_retry:
            return None
        return self._set(document_id, status=DocumentStatus.INDEXING, failure_reason=None)

    async def mark_failed(self, document_id: uuid.UUID, reason: FailureReason) -> None:
        if self.documents[document_id].status is DocumentStatus.INDEXING:
            self._set(document_id, status=DocumentStatus.FAILED, failure_reason=reason)

    async def store_chunks_and_mark_ready(
        self, document_id: uuid.UUID, chunks: Sequence[Chunk], embeddings: Sequence[list[float]]
    ) -> None:
        list(zip(chunks, embeddings, strict=True))  # same length check as the adapter
        self.chunks[document_id] = list(chunks)
        self._set(document_id, status=DocumentStatus.READY, chunk_count=len(chunks))

    async def fail_interrupted_indexing(self) -> int:
        stuck = [d.id for d in self.documents.values() if d.status is DocumentStatus.INDEXING]
        for document_id in stuck:
            self._set(
                document_id,
                status=DocumentStatus.FAILED,
                failure_reason=FailureReason.INDEXING_FAILED,
            )
        return len(stuck)

    def _set(self, document_id: uuid.UUID, **changes: Any) -> Document:
        document = replace(self.documents[document_id], **changes)
        self.documents[document_id] = document
        return document
