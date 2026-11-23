import hashlib
import uuid

import pytest

from app.application.ingestion import IngestionService
from app.application.ports import EmbeddingPort
from app.domain.documents import (
    Document,
    DocumentNotFound,
    DocumentStatus,
    EmbeddingDimensionMismatch,
    EmptyFile,
    FailureReason,
    FileTooLarge,
    UnsupportedFormat,
)
from tests.factories import (
    EMBEDDING_DIMENSIONS,
    MAX_UPLOAD_BYTES,
    blank_pdf,
    fixture_bytes,
    make_ingestion,
)
from tests.fakes import (
    FailingEmbeddings,
    FakeEmbeddings,
    FixedVectorSchema,
    InMemoryDocumentRepository,
    MisconfiguredEmbeddings,
    StalledParser,
)

OWNER = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _service(
    repository: InMemoryDocumentRepository,
    embeddings: EmbeddingPort | None = None,
    max_upload_bytes: int = MAX_UPLOAD_BYTES,
) -> IngestionService:
    return make_ingestion(repository, embeddings or FakeEmbeddings(8), max_upload_bytes)


async def _upload_and_index(service: IngestionService, filename: str) -> Document:
    content = fixture_bytes(filename)
    result = await service.upload(OWNER, filename, content)
    await service.index(result.document, content)
    return await service.get(OWNER, result.document.id)


async def test_upload_registers_a_new_document_for_indexing() -> None:
    repository = InMemoryDocumentRepository()
    content = fixture_bytes("expense-policy.pdf")

    result = await _service(repository).upload(OWNER, "C:\\docs\\expense-policy.pdf", content)

    assert result.needs_indexing is True
    assert result.document.status is DocumentStatus.INDEXING
    assert result.document.filename == "expense-policy.pdf"
    assert result.document.sha256 == hashlib.sha256(content).hexdigest()
    assert result.document.owner_id == OWNER


async def test_upload_unsupported_type_raises() -> None:
    service = _service(InMemoryDocumentRepository())

    with pytest.raises(UnsupportedFormat):
        await service.upload(OWNER, "unsupported.docx", fixture_bytes("unsupported.docx"))


async def test_upload_empty_file_raises() -> None:
    with pytest.raises(EmptyFile):
        await _service(InMemoryDocumentRepository()).upload(OWNER, "empty.txt", b"")


async def test_upload_file_too_large_raises() -> None:
    service = _service(InMemoryDocumentRepository(), max_upload_bytes=10)

    with pytest.raises(FileTooLarge):
        await service.upload(OWNER, "office-handbook.txt", fixture_bytes("office-handbook.txt"))


async def test_upload_duplicate_returns_the_existing_document_without_indexing() -> None:
    service = _service(InMemoryDocumentRepository())
    ready = await _upload_and_index(service, "office-handbook.txt")

    result = await service.upload(OWNER, "copy.txt", fixture_bytes("office-handbook.txt"))

    assert result.needs_indexing is False
    assert result.document == ready


async def test_upload_duplicate_after_a_transient_failure_indexes_again() -> None:
    repository = InMemoryDocumentRepository()
    failed = await _upload_and_index(
        _service(repository, FailingEmbeddings()), "office-handbook.txt"
    )

    result = await _service(repository).upload(
        OWNER, "office-handbook.txt", fixture_bytes("office-handbook.txt")
    )

    assert result.needs_indexing is True
    assert result.document.id == failed.id
    assert result.document.status is DocumentStatus.INDEXING
    assert result.document.failure_reason is None


async def test_upload_duplicate_without_extractable_text_is_returned_as_is() -> None:
    service = _service(InMemoryDocumentRepository())
    failed = await _upload_and_index(service, "scanned-notice.pdf")

    result = await service.upload(OWNER, "scanned-notice.pdf", fixture_bytes("scanned-notice.pdf"))

    assert result.needs_indexing is False
    assert result.document == failed


async def test_index_pdf_stores_chunks_with_pages_and_marks_ready() -> None:
    repository = InMemoryDocumentRepository()

    document = await _upload_and_index(_service(repository), "remote-work-policy.pdf")

    assert document.status is DocumentStatus.READY
    assert document.chunk_count == len(repository.chunks[document.id]) > 0
    assert {chunk.page for chunk in repository.chunks[document.id]} == {1, 2}


@pytest.mark.parametrize("filename", ["parental-leave-policy.md", "office-handbook.txt"])
async def test_index_markdown_and_text_marks_ready(filename: str) -> None:
    document = await _upload_and_index(_service(InMemoryDocumentRepository()), filename)

    assert document.status is DocumentStatus.READY
    assert document.chunk_count > 0


async def test_index_without_extractable_text_fails_permanently() -> None:
    document = await _upload_and_index(_service(InMemoryDocumentRepository()), "scanned-notice.pdf")

    assert document.status is DocumentStatus.FAILED
    assert document.failure_reason is FailureReason.NO_EXTRACTABLE_TEXT
    assert document.can_retry is False


async def test_index_embedding_failure_fails_transiently() -> None:
    document = await _upload_and_index(
        _service(InMemoryDocumentRepository(), FailingEmbeddings()), "expense-policy.pdf"
    )

    assert document.status is DocumentStatus.FAILED
    assert document.failure_reason is FailureReason.INDEXING_FAILED
    assert document.can_retry is True


async def test_ingestion_provider_misconfigured() -> None:
    """DOM-25: a rejected key or model is not reported as a temporary failure."""
    document = await _upload_and_index(
        _service(InMemoryDocumentRepository(), MisconfiguredEmbeddings()), "expense-policy.pdf"
    )

    assert document.status is DocumentStatus.FAILED
    assert document.failure_reason is FailureReason.PROVIDER_MISCONFIGURED
    assert document.failure_message is not None
    assert "OPENAI_API_KEY" in document.failure_message
    assert document.can_retry is True


async def test_ingestion_provider_misconfigured_retry() -> None:
    """DOM-04: once the operator fixes the settings, re-uploading the same file indexes it."""
    repository = InMemoryDocumentRepository()
    failed = await _upload_and_index(
        _service(repository, MisconfiguredEmbeddings()), "office-handbook.txt"
    )

    fixed = _service(repository)
    document = await _upload_and_index(fixed, "office-handbook.txt")

    assert document.id == failed.id
    assert document.status is DocumentStatus.READY
    assert document.failure_reason is None


async def test_ingestion_dimension_mismatch_rejects_the_upload_before_storing() -> None:
    repository = InMemoryDocumentRepository()
    service = make_ingestion(
        repository, FakeEmbeddings(8), schema=FixedVectorSchema(EMBEDDING_DIMENSIONS + 1)
    )

    with pytest.raises(EmbeddingDimensionMismatch) as raised:
        await service.upload(OWNER, "office-handbook.txt", fixture_bytes("office-handbook.txt"))

    assert (raised.value.configured, raised.value.stored) == (
        EMBEDDING_DIMENSIONS,
        EMBEDDING_DIMENSIONS + 1,
    )
    assert repository.documents == {}


async def test_check_embedding_dimensions_remembers_a_match() -> None:
    schema = FixedVectorSchema(EMBEDDING_DIMENSIONS)
    service = make_ingestion(InMemoryDocumentRepository(), FakeEmbeddings(8), schema=schema)

    await service.check_embedding_dimensions()
    await service.check_embedding_dimensions()

    assert schema.reads == 1


async def test_check_embedding_dimensions_unreadable_column_does_not_block() -> None:
    schema = FixedVectorSchema(None)
    service = make_ingestion(InMemoryDocumentRepository(), FakeEmbeddings(8), schema=schema)

    await service.check_embedding_dimensions()
    await service.check_embedding_dimensions()

    assert schema.reads == 2  # not remembered: read again until it can be checked


async def test_get_document_of_another_owner_raises_not_found() -> None:
    service = _service(InMemoryDocumentRepository())
    result = await service.upload(
        OWNER, "office-handbook.txt", fixture_bytes("office-handbook.txt")
    )

    with pytest.raises(DocumentNotFound):
        await service.get(uuid.uuid4(), result.document.id)


async def test_list_for_owner_returns_the_owner_documents() -> None:
    service = _service(InMemoryDocumentRepository())
    result = await service.upload(
        OWNER, "office-handbook.txt", fixture_bytes("office-handbook.txt")
    )
    await service.upload(uuid.uuid4(), "office-handbook.txt", fixture_bytes("office-handbook.txt"))

    assert await service.list_for_owner(OWNER) == [result.document]


async def test_recover_interrupted_fails_documents_left_indexing() -> None:
    service = _service(InMemoryDocumentRepository())
    result = await service.upload(
        OWNER, "office-handbook.txt", fixture_bytes("office-handbook.txt")
    )

    recovered = await service.recover_interrupted()

    document = await service.get(OWNER, result.document.id)
    assert recovered == 1
    assert document.status is DocumentStatus.FAILED
    assert document.failure_reason is FailureReason.INDEXING_FAILED


async def test_upload_retry_already_started_is_not_scheduled_twice() -> None:
    repository = InMemoryDocumentRepository()
    content = fixture_bytes("office-handbook.txt")
    await _upload_and_index(_service(repository, FailingEmbeddings()), "office-handbook.txt")
    service = _service(repository)
    first = await service.upload(OWNER, "office-handbook.txt", content)

    second = await service.upload(OWNER, "office-handbook.txt", content)

    assert first.needs_indexing is True
    assert second.needs_indexing is False
    assert second.document.status is DocumentStatus.INDEXING


class _RepositoryDownAfterUpload(InMemoryDocumentRepository):
    async def mark_failed(self, document_id: uuid.UUID, reason: FailureReason) -> None:
        raise ConnectionError("database went away")


async def test_index_failure_that_cannot_be_recorded_does_not_raise() -> None:
    repository = _RepositoryDownAfterUpload()
    service = _service(repository, FailingEmbeddings())
    content = fixture_bytes("office-handbook.txt")
    result = await service.upload(OWNER, "office-handbook.txt", content)

    await service.index(result.document, content)  # background job: must not raise

    assert repository.documents[result.document.id].status is DocumentStatus.INDEXING


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("quarterly-report.pdf", b"\x89PNG\r\n\x1a\n renamed image"),
        ("notes.txt", b"caf\xe9 latin-1"),
        ("notes.md", b"# Notes\x00"),
    ],
    ids=["renamed-binary", "invalid-utf8", "nul-byte"],
)
async def test_upload_content_not_matching_the_extension_raises(
    filename: str, content: bytes
) -> None:
    repository = InMemoryDocumentRepository()

    with pytest.raises(UnsupportedFormat, match="does not match"):
        await _service(repository).upload(OWNER, filename, content)

    assert await repository.list_for_owner(OWNER) == []  # DOM-01: rejected before storing


async def test_index_pdf_over_the_page_limit_fails_permanently() -> None:
    repository = InMemoryDocumentRepository()
    service = make_ingestion(repository, FakeEmbeddings(8), pdf_max_pages=3)
    content = blank_pdf(4)
    result = await service.upload(OWNER, "huge.pdf", content)

    await service.index(result.document, content)
    document = await service.get(OWNER, result.document.id)
    again = await service.upload(OWNER, "huge.pdf", content)

    assert document.failure_reason is FailureReason.TOO_MANY_PAGES
    assert "Split it" in (document.failure_message or "")
    assert document.can_retry is False
    assert again.needs_indexing is False  # DOM-04: permanent, returned as is


async def test_index_pdf_parse_over_the_time_budget_fails_permanently() -> None:
    repository = InMemoryDocumentRepository()
    parser = StalledParser()
    service = make_ingestion(
        repository, FakeEmbeddings(8), parser=parser, pdf_parse_timeout_seconds=0.01
    )
    content = fixture_bytes("expense-policy.pdf")
    result = await service.upload(OWNER, "expense-policy.pdf", content)

    await service.index(result.document, content)
    document = await service.get(OWNER, result.document.id)

    assert document.failure_reason is FailureReason.PARSE_TIMEOUT
    assert "took too long" in (document.failure_message or "")
    assert document.can_retry is False
    assert parser.cancelled is True  # DOM-28: the parse is cancelled, not left running
