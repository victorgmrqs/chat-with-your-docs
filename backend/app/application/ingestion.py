"""Document ingestion use cases: upload, background indexing, lookup and restart recovery."""

import asyncio
import hashlib
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from app.application import telemetry as t
from app.application.ports import (
    DocumentParser,
    DocumentRepository,
    EmbeddingMisconfigured,
    EmbeddingPort,
    TextSplitter,
    VectorSchemaPort,
)
from app.domain.documents import (
    ACCEPTED_FORMATS_HINT,
    Document,
    DocumentFormat,
    DocumentNotFound,
    DocumentStatus,
    EmbeddingDimensionMismatch,
    EmptyFile,
    FailureReason,
    FileTooLarge,
    NoExtractableText,
    ParseTimeout,
    Section,
    TooManyPages,
    build_chunks,
    check_content,
    clean_filename,
    detect_format,
)
from app.domain.usage import PriceTable, TokenUsage

logger = logging.getLogger(__name__)


def _log_failure(
    message: str, document: Document, exc: Exception, level: int = logging.WARNING
) -> None:
    error_type = type(exc).__name__
    logger.log(
        level,
        message,
        document.id,
        error_type,
        extra={"document_id": str(document.id), "error_type": error_type},
    )


def _log_indexed(
    document: Document, chunks: int, usage: Sequence[TokenUsage], cost: float | None
) -> None:
    """DOM-24: ids and numbers only; tokens and cost are null when unknown, never 0."""
    tokens = sum(u.input_tokens for u in usage) if usage else None
    logger.info(
        "Indexed document %s: %d chunks, %s embedding tokens, estimated cost %s USD",
        document.id,
        chunks,
        tokens,
        cost,
        extra={
            "document_id": str(document.id),
            "chunks": chunks,
            "embedding_tokens": tokens,
            "cost_usd": cost,
        },
    )


@dataclass(frozen=True, slots=True)
class UploadResult:
    document: Document
    needs_indexing: bool  # True: the caller schedules `index` (202); False: returned as is (200)


class IngestionService:
    def __init__(
        self,
        repository: DocumentRepository,
        parser: DocumentParser,
        splitter: TextSplitter,
        embeddings: EmbeddingPort,
        schema: VectorSchemaPort,
        *,
        max_upload_bytes: int,
        embedding_dimensions: int,
        pdf_parse_timeout_seconds: float,
        prices: PriceTable | None = None,
    ) -> None:
        self._repository = repository
        self._parser = parser
        self._splitter = splitter
        self._embeddings = embeddings
        self._schema = schema
        self._max_upload_bytes = max_upload_bytes
        self._embedding_dimensions = embedding_dimensions
        self._pdf_parse_timeout = pdf_parse_timeout_seconds
        self._prices = prices or PriceTable()  # empty: no cost recorded (DOM-24)
        self._dimensions_match = False

    async def check_embedding_dimensions(self) -> None:
        """DOM-26: raises EmbeddingDimensionMismatch when EMBEDDING_DIMENSIONS differs from
        the stored column. A match is remembered: the column only changes with a migration,
        and the setting with a restart. Raises DatabaseUnavailable."""
        if self._dimensions_match:
            return
        stored = await self._schema.embedding_dimensions()
        if stored is not None and stored != self._embedding_dimensions:
            raise EmbeddingDimensionMismatch(self._embedding_dimensions, stored)
        self._dimensions_match = stored is not None

    async def upload(self, owner_id: uuid.UUID, filename: str, content: bytes) -> UploadResult:
        """Validate and register the file; indexing itself runs later through `index`."""
        name = clean_filename(filename)
        document_format = detect_format(name)  # DOM-01: raises UnsupportedFormat
        if not content:
            raise EmptyFile(f"The file is empty. {ACCEPTED_FORMATS_HINT}")
        if len(content) > self._max_upload_bytes:
            raise FileTooLarge(self._max_upload_bytes // (1024 * 1024))
        check_content(document_format, content)  # DOM-01: raises UnsupportedFormat
        await self.check_embedding_dimensions()  # DOM-26: before anything is stored

        now = datetime.now(UTC)
        candidate = Document(
            id=uuid.uuid4(),
            owner_id=owner_id,  # DOM-06: set by the application, never by the client
            filename=name,
            format=document_format,
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
            status=DocumentStatus.INDEXING,
            failure_reason=None,
            chunk_count=0,
            created_at=now,
            updated_at=now,
        )
        document, created = await self._repository.create_or_get(candidate)
        if created:
            return UploadResult(document, needs_indexing=True)
        if document.can_retry:  # DOM-04: only a failure that does not depend on the file
            retried = await self._repository.mark_indexing(document.id)
            if retried is not None:
                return UploadResult(retried, needs_indexing=True)
            # A concurrent upload started the retry first: report the current state.
            document = await self._repository.get(owner_id, document.id) or document
        return UploadResult(document, needs_indexing=False)

    async def index(self, document: Document, content: bytes) -> None:
        """Background job: parse, split, embed and store. Always ends Ready or Failed (DOM-02).

        One trace per run (`ingest.document`), found by `app.document.id` (DOM-23).
        """
        with t.step(
            t.INGEST,
            {
                t.DOCUMENT_ID: str(document.id),
                t.DOCUMENT_FORMAT: document.format.value,
                t.DOCUMENT_BYTES: len(content),
            },
        ) as span:
            reason = await self._index(document, content)
            if reason is None:
                span.set_attribute(t.DOCUMENT_STATUS, DocumentStatus.READY.value)
                return
            span.set_attributes(
                {
                    t.DOCUMENT_STATUS: DocumentStatus.FAILED.value,
                    t.DOCUMENT_FAILURE_REASON: reason.value,
                }
            )
            try:
                await self._repository.mark_failed(document.id, reason)
            except Exception as exc:
                # Database gone mid-job: the document stays `indexing` until startup recovery.
                _log_failure("Could not record the failure of document %s: %s", document, exc)
                t.mark_failed(span, exc)

    async def _index(self, document: Document, content: bytes) -> FailureReason | None:
        """None when the document is Ready; otherwise why it failed (DOM-03)."""
        try:
            with t.step(t.INGEST_PARSE) as span:
                sections = await self._parse(document, content)
                span.set_attribute(t.DOCUMENT_SECTIONS, len(sections))
            with t.step(t.INGEST_CHUNK) as span:
                # CPU-bound on large files: keep the event loop free for polling and health checks.
                pieces = await asyncio.to_thread(self._splitter.split, sections)
                chunks = build_chunks(document, pieces)
                span.set_attribute(t.DOCUMENT_CHUNKS, len(chunks))
            with t.step(t.INGEST_EMBED, {t.EMBEDDED_TEXTS: len(chunks)}) as span:
                embedding = await self._embeddings.embed_documents(
                    [c.embedding_text for c in chunks]
                )
                t.record_usage(span, embedding.usage)  # DOM-24
                cost = t.record_cost(span, self._prices, embedding.usage)
            with t.step(t.INGEST_STORE, {t.DOCUMENT_CHUNKS: len(chunks)}):
                await self._repository.store_chunks_and_mark_ready(
                    document.id, chunks, embedding.value
                )
            _log_indexed(document, len(chunks), embedding.usage, cost)
            return None
        except NoExtractableText:
            # A permanent property of the file, not a system failure: the parse span shows it.
            return FailureReason.NO_EXTRACTABLE_TEXT
        except TooManyPages:
            return FailureReason.TOO_MANY_PAGES  # DOM-28, permanent like the case above
        except ParseTimeout:
            return FailureReason.PARSE_TIMEOUT  # DOM-28
        except EmbeddingMisconfigured as exc:
            # DOM-25: the operator must fix the key or model; every upload fails until then.
            _log_failure(
                "Embeddings provider rejected the configuration for document %s: %s",
                document,
                exc,
                logging.ERROR,
            )
            t.mark_failed(t.current_span(), exc)
            return FailureReason.PROVIDER_MISCONFIGURED
        except Exception as exc:
            # DOM-03: anything else (provider or storage) is transient. Log the type only:
            # driver errors can carry statement parameters, i.e. chunk text.
            _log_failure("Indexing failed for document %s: %s", document, exc)
            t.mark_failed(t.current_span(), exc)  # the root: no step is open here
            return FailureReason.INDEXING_FAILED

    async def _parse(self, document: Document, content: bytes) -> list[Section]:
        """DOM-28: a PDF gets PDF_PARSE_TIMEOUT_SECONDS; the timeout cancels the parse."""
        if document.format is not DocumentFormat.PDF:
            return await self._parser.parse(content, document.format)
        try:
            async with asyncio.timeout(self._pdf_parse_timeout):
                return await self._parser.parse(content, document.format)
        except TimeoutError:
            raise ParseTimeout("PDF parse over budget") from None

    async def get(self, owner_id: uuid.UUID, document_id: uuid.UUID) -> Document:
        document = await self._repository.get(owner_id, document_id)
        if document is None:
            raise DocumentNotFound
        return document

    async def list_for_owner(self, owner_id: uuid.UUID) -> list[Document]:
        return await self._repository.list_for_owner(owner_id)

    async def recover_interrupted(self) -> int:
        """DOM-03: run once at startup; jobs do not survive a restart (single API process)."""
        return await self._repository.fail_interrupted_indexing()
