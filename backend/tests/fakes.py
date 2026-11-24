"""Declared fakes implementing the application ports. No network calls in tests."""

import asyncio
import hashlib
import math
import re
import uuid
from collections.abc import Callable, Sequence
from dataclasses import replace
from html import unescape
from typing import Any

from pydantic import BaseModel

from app.application.ports import (
    ChatPrompt,
    DocumentNotIndexing,
    EmbeddingMisconfigured,
    EmbeddingUnavailable,
    Generation,
)
from app.domain.answers import RetrievedChunk
from app.domain.documents import (
    Chunk,
    Document,
    DocumentFormat,
    DocumentStatus,
    FailureReason,
    Section,
)
from app.domain.usage import TokenUsage

EMBEDDING_MODEL = "fake-embedding-model"
EMBEDDING_TOKENS_PER_TEXT = 5


def embedding_usage(texts: Sequence[str]) -> tuple[TokenUsage, ...]:
    """What the embedding fakes report for one call (DOM-24): a fixed count per text."""
    return (TokenUsage(EMBEDDING_MODEL, EMBEDDING_TOKENS_PER_TEXT * len(texts), 0),)


class FakeEmbeddings:
    """Deterministic vectors derived from the text hash: same text, same vector.
    Reports `embedding_usage(texts)`, as a provider would, unless `reports_usage=False`."""

    def __init__(self, dimensions: int, *, reports_usage: bool = True) -> None:
        self.dimensions = dimensions
        self._reports_usage = reports_usage

    async def embed_documents(self, texts: Sequence[str]) -> Generation[list[list[float]]]:
        usage = embedding_usage(texts) if self._reports_usage else ()
        return Generation([self._vector(text) for text in texts], usage)

    def _vector(self, text: str) -> list[float]:
        seed = hashlib.sha256(text.encode()).digest()
        return [seed[i % len(seed)] / 255 for i in range(self.dimensions)]


class FailingEmbeddings:
    """Provider still failing after the adapter's retries (transient failure)."""

    async def embed_documents(self, texts: Sequence[str]) -> Generation[list[list[float]]]:
        raise EmbeddingUnavailable("provider unavailable")


class MisconfiguredEmbeddings:
    """Provider rejecting the API key or model (DOM-25): fails until the settings change."""

    async def embed_documents(self, texts: Sequence[str]) -> Generation[list[list[float]]]:
        raise EmbeddingMisconfigured("AuthenticationError")


class StalledParser:
    """A parse that never finishes on its own: only the DOM-28 timeout ends it (no real wait)."""

    def __init__(self) -> None:
        self.cancelled = False

    async def parse(self, content: bytes, document_format: DocumentFormat) -> list[Section]:
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        raise AssertionError("unreachable")


class FixedVectorSchema:
    """VectorSchemaPort with a fixed column dimension (None: column not readable)."""

    def __init__(self, dimensions: int | None) -> None:
        self.dimensions = dimensions
        self.reads = 0

    async def embedding_dimensions(self) -> int | None:
        self.reads += 1
        return self.dimensions


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
        if self.documents[document_id].status is not DocumentStatus.INDEXING:
            raise DocumentNotIndexing(str(document_id))
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


_STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "can",
        "do",
        "does",
        "for",
        "from",
        "how",
        "i",
        "in",
        "is",
        "it",
        "my",
        "of",
        "on",
        "or",
        "the",
        "this",
        "to",
        "what",
        "when",
        "which",
        "who",
        "why",
        "with",
    ]
)


class KeywordEmbeddings:
    """Bag-of-words vectors: cosine similarity reflects shared words (no semantics).

    Lets tests exercise the vector branch and the relevance gate without a provider.
    Reports `embedding_usage(texts)`.
    """

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    async def embed_documents(self, texts: Sequence[str]) -> Generation[list[list[float]]]:
        return Generation([self._vector(text) for text in texts], embedding_usage(texts))

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            if word not in _STOPWORDS:
                digest = hashlib.sha256(word.encode()).digest()
                vector[int.from_bytes(digest[:4]) % self.dimensions] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:  # only stopwords: any fixed non-zero vector (cosine needs a norm)
            vector[0] = 1.0
            return vector
        return [value / norm for value in vector]


_SOURCE = re.compile(r'<source id="(S\d+)"[^>]*>\n(.*?)\n</source>', re.DOTALL)


def prompt_sources(prompt: ChatPrompt) -> dict[str, str]:
    """Label -> unescaped text of each source the use case put in the prompt (oracle fakes)."""
    return {label: unescape(body) for label, body in _SOURCE.findall(prompt.user)}


Reply = BaseModel | Exception | Callable[[ChatPrompt], BaseModel]


class FakeChatModel:
    """ChatModelPort returning scripted replies in call order; records every prompt.

    A reply is a schema instance, an exception to raise, or a callable that builds the
    instance from the prompt (for tests that need the labels the use case assigned).
    Every successful call reports USAGE_PER_CALL, as a provider would (DOM-24), unless
    `reports_usage` says otherwise: False for every call, or one flag per call in order
    (a provider that returns no usage metadata).
    """

    provider = "fake"
    model = "fake-chat-model"
    USAGE_PER_CALL = TokenUsage("fake-chat-model-2026", input_tokens=100, output_tokens=20)

    def __init__(self, *replies: Reply, reports_usage: bool | Sequence[bool] = True) -> None:
        self._replies = list(replies)
        self._reports_usage = reports_usage if isinstance(reports_usage, bool) else [*reports_usage]
        self.prompts: list[ChatPrompt] = []

    async def generate[T: BaseModel](self, prompt: ChatPrompt, schema: type[T]) -> Generation[T]:
        self.prompts.append(prompt)
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        result = reply if isinstance(reply, BaseModel) else reply(prompt)
        if not isinstance(result, schema):
            raise TypeError(f"scripted reply {type(result).__name__} is not a {schema.__name__}")
        reports = self._reports_usage
        if not isinstance(reports, bool):
            reports = reports.pop(0)
        return Generation(result, (self.USAGE_PER_CALL,) if reports else ())


class FakeRetriever:
    """RetrieverPort returning fixed chunks (at most `limit`)."""

    def __init__(self, chunks: Sequence[RetrievedChunk] = (), *, has_ready: bool = True) -> None:
        self.chunks = list(chunks)
        self.has_ready = has_ready

    async def has_ready_documents(self, owner_id: uuid.UUID) -> bool:
        return self.has_ready

    async def search(
        self,
        owner_id: uuid.UUID,
        query_text: str,
        query_embedding: Sequence[float],
        *,
        candidates: int,
        limit: int,
    ) -> list[RetrievedChunk]:
        return self.chunks[:limit]
