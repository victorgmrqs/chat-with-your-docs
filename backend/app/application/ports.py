"""Ports the use cases depend on. Adapters in app/adapters implement them."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel

from app.domain.answers import RetrievedChunk
from app.domain.documents import Chunk, Document, DocumentFormat, FailureReason, Section


@dataclass(frozen=True, slots=True)
class ChatPrompt:
    system: str
    user: str


class ChatModelPort(Protocol):
    """Structured-output chat model (OpenAI or Anthropic, chosen by configuration, DOM-13)."""

    @property
    def provider(self) -> str: ...

    @property
    def model(self) -> str: ...

    async def generate[T: BaseModel](self, prompt: ChatPrompt, schema: type[T]) -> T:
        """A validated instance of `schema`.

        Raises ChatModelTimeout or ChatModelUnavailable (DOM-12) after the adapter's retries.
        """
        ...


class RetrieverPort(Protocol):
    async def has_ready_documents(self, owner_id: uuid.UUID) -> bool: ...

    async def search(
        self,
        owner_id: uuid.UUID,
        query_text: str,
        query_embedding: Sequence[float],
        *,
        candidates: int,
        limit: int,
    ) -> list[RetrievedChunk]:
        """Hybrid search over the owner's Ready chunks (DOM-07), best fused score first.

        `candidates` per branch (vector, full-text) before fusion; `limit` after it.
        """
        ...


class RerankerPort(Protocol):
    async def rerank(
        self, question: str, chunks: Sequence[RetrievedChunk], top_n: int
    ) -> list[RetrievedChunk]:
        """At most `top_n` of `chunks`, most relevant first. Raises like ChatModelPort."""
        ...


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
