"""Ports the use cases depend on. Adapters in app/adapters implement them."""

import uuid
from collections.abc import Sequence
from typing import Protocol

from app.domain.documents import Chunk, Document, DocumentFormat, FailureReason, Section


class EmbeddingUnavailable(Exception):
    """The embeddings provider failed after the adapter's own retries (transient)."""


class DocumentParser(Protocol):
    async def parse(self, content: bytes, document_format: DocumentFormat) -> list[Section]:
        """Text per page (PDF), heading section (Markdown) or whole file (text).

        Raises NoExtractableText when the file has no usable text.
        """
        ...


class TextSplitter(Protocol):
    def split(self, sections: Sequence[Section]) -> list[Section]:
        """Chunk-sized pieces; each keeps the page/heading of its section."""
        ...


class EmbeddingPort(Protocol):
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """One vector per text, same order. Raises EmbeddingUnavailable."""
        ...


class DocumentRepository(Protocol):
    async def create_or_get(self, document: Document) -> tuple[Document, bool]:
        """Insert, or return the owner's document with the same SHA-256 (created=False)."""
        ...

    async def get(self, owner_id: uuid.UUID, document_id: uuid.UUID) -> Document | None: ...

    async def list_for_owner(self, owner_id: uuid.UUID) -> list[Document]: ...

    async def mark_indexing(self, document_id: uuid.UUID) -> Document | None:
        """DOM-04: `indexing_failed` → `indexing`; None if not in that state (lost a race)."""
        ...

    async def mark_failed(self, document_id: uuid.UUID, reason: FailureReason) -> None:
        """Fail an `indexing` document; any other state is left as is."""
        ...

    async def store_chunks_and_mark_ready(
        self, document_id: uuid.UUID, chunks: Sequence[Chunk], embeddings: Sequence[list[float]]
    ) -> None:
        """Replace the document's chunks and set it Ready in one transaction (DOM-02)."""
        ...

    async def fail_interrupted_indexing(self) -> int:
        """Documents left `indexing` by a restart become `indexing_failed` (DOM-03)."""
        ...
