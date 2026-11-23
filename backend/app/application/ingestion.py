"""Document ingestion use cases: upload, background indexing, lookup and restart recovery."""

import asyncio
import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from app.application import telemetry as t
from app.application.ports import (
    DocumentParser,
    DocumentRepository,
    EmbeddingPort,
    TextSplitter,
)
from app.domain.documents import (
    ACCEPTED_FORMATS_HINT,
    Document,
    DocumentNotFound,
    DocumentStatus,
    EmptyFile,
    FailureReason,
    FileTooLarge,
    NoExtractableText,
    build_chunks,
    clean_filename,
    detect_format,
)

logger = logging.getLogger(__name__)


def _log_failure(message: str, document: Document, exc: Exception) -> None:
    error_type = type(exc).__name__
    logger.warning(
        message,
        document.id,
        error_type,
        extra={"document_id": str(document.id), "error_type": error_type},
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
        *,
        max_upload_bytes: int,
    ) -> None:
        self._repository = repository
        self._parser = parser
        self._splitter = splitter
        self._embeddings = embeddings
        self._max_upload_bytes = max_upload_bytes

    async def upload(self, owner_id: uuid.UUID, filename: str, content: bytes) -> UploadResult:
        """Validate and register the file; indexing itself runs later through `index`."""
        name = clean_filename(filename)
        document_format = detect_format(name)  # DOM-01: raises UnsupportedFormat
        if not content:
            raise EmptyFile(f"The file is empty. {ACCEPTED_FORMATS_HINT}")
        if len(content) > self._max_upload_bytes:
            limit_mb = self._max_upload_bytes // (1024 * 1024)
            raise FileTooLarge(f"The file is larger than {limit_mb} MB. Upload a smaller file.")

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
        if document.can_retry:  # DOM-04: only a transient failure is indexed again
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
                sections = await self._parser.parse(content, document.format)
                span.set_attribute(t.DOCUMENT_SECTIONS, len(sections))
            with t.step(t.INGEST_CHUNK) as span:
                # CPU-bound on large files: keep the event loop free for polling and health checks.
                pieces = await asyncio.to_thread(self._splitter.split, sections)
                chunks = build_chunks(document, pieces)
                span.set_attribute(t.DOCUMENT_CHUNKS, len(chunks))
            with t.step(t.INGEST_EMBED, {t.EMBEDDED_TEXTS: len(chunks)}):
                embeddings = await self._embeddings.embed_documents(
                    [c.embedding_text for c in chunks]
                )
            with t.step(t.INGEST_STORE, {t.DOCUMENT_CHUNKS: len(chunks)}):
                await self._repository.store_chunks_and_mark_ready(document.id, chunks, embeddings)
            return None
        except NoExtractableText:
            # A permanent property of the file, not a system failure: the parse span shows it.
            return FailureReason.NO_EXTRACTABLE_TEXT
        except Exception as exc:
            # DOM-03: anything else (provider or storage) is transient. Log the type only:
            # driver errors can carry statement parameters, i.e. chunk text.
            _log_failure("Indexing failed for document %s: %s", document, exc)
            t.mark_failed(t.current_span(), exc)  # the root: no step is open here
            return FailureReason.INDEXING_FAILED

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
