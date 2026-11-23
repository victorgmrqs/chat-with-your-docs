import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.adapters.postgres_documents import PostgresDocumentRepository
from app.application.ports import DocumentNotIndexing
from app.domain.documents import (
    RETRYABLE_FAILURES,
    Chunk,
    Document,
    DocumentStatus,
    FailureReason,
    Section,
    build_chunks,
)
from tests.factories import (
    EMBEDDING_DIMENSIONS,
    fixture_bytes,
    make_document,
    make_ingestion,
    stored_chunks,
)
from tests.fakes import FakeEmbeddings, StalledParser

pytestmark = pytest.mark.integration


async def test_create_or_get_inserts_a_new_document(
    repository: PostgresDocumentRepository,
) -> None:
    document = make_document()

    stored, created = await repository.create_or_get(document)

    assert created is True
    assert stored == document


async def test_create_or_get_returns_the_existing_document_for_the_same_owner_and_hash(
    repository: PostgresDocumentRepository,
) -> None:
    first = make_document()
    await repository.create_or_get(first)
    duplicate = make_document(owner_id=first.owner_id, sha256=first.sha256, filename="copy.pdf")

    stored, created = await repository.create_or_get(duplicate)

    assert created is False
    assert stored == first


async def test_create_or_get_same_hash_for_another_owner_creates_a_new_document(
    repository: PostgresDocumentRepository,
) -> None:
    mine = make_document(sha256="a" * 64)
    theirs = make_document(sha256="a" * 64)
    await repository.create_or_get(mine)

    stored, created = await repository.create_or_get(theirs)

    assert created is True
    assert stored == theirs


async def test_get_returns_the_owner_document(repository: PostgresDocumentRepository) -> None:
    document = make_document()
    await repository.create_or_get(document)

    assert await repository.get(document.owner_id, document.id) == document


async def test_get_hides_documents_of_other_owners(
    repository: PostgresDocumentRepository,
) -> None:
    document = make_document()
    await repository.create_or_get(document)

    assert await repository.get(uuid.uuid4(), document.id) is None


async def test_get_unknown_document_returns_none(repository: PostgresDocumentRepository) -> None:
    assert await repository.get(uuid.uuid4(), uuid.uuid4()) is None


async def test_list_for_owner_returns_only_the_owner_documents_newest_first(
    repository: PostgresDocumentRepository,
) -> None:
    owner_id = uuid.uuid4()
    now = datetime.now(UTC)
    older = make_document(owner_id=owner_id, sha256="1" * 64, created_at=now - timedelta(hours=1))
    newer = make_document(owner_id=owner_id, sha256="2" * 64, created_at=now)
    for document in (older, newer, make_document()):  # the last one belongs to another owner
        await repository.create_or_get(document)

    assert await repository.list_for_owner(owner_id) == [newer, older]


async def _indexed_input(
    repository: PostgresDocumentRepository,
) -> tuple[Document, list[Chunk], list[list[float]]]:
    """A stored `indexing` document with two chunks (pages 1 and 2) and their embeddings."""
    document, _ = await repository.create_or_get(make_document())
    sections = [
        Section(text="Remote work requires prior manager approval.", page=1),
        Section(text="Coworking reimbursement is limited to US$ 250.", page=2),
    ]
    chunks = build_chunks(document, sections)
    embedding = await FakeEmbeddings(EMBEDDING_DIMENSIONS).embed_documents(
        [c.embedding_text for c in chunks]
    )
    return document, chunks, embedding.value


async def _locations(
    engine: AsyncEngine, document_id: uuid.UUID
) -> list[tuple[int, int | None, str | None]]:
    return [(c.chunk_index, c.page, c.heading) for c in await stored_chunks(engine, document_id)]


async def test_store_chunks_and_mark_ready_persists_chunks_and_sets_ready(
    repository: PostgresDocumentRepository, engine: AsyncEngine
) -> None:
    document, chunks, embeddings = await _indexed_input(repository)

    await repository.store_chunks_and_mark_ready(document.id, chunks, embeddings)

    stored = await repository.get(document.owner_id, document.id)
    assert stored is not None
    assert stored.status is DocumentStatus.READY
    assert stored.chunk_count == 2
    assert await _locations(engine, document.id) == [(0, 1, None), (1, 2, None)]
    assert {c.owner_id for c in await stored_chunks(engine, document.id)} == {document.owner_id}


async def test_store_chunks_and_mark_ready_on_a_ready_document_keeps_its_chunks(
    repository: PostgresDocumentRepository, engine: AsyncEngine
) -> None:
    document, chunks, embeddings = await _indexed_input(repository)
    await repository.store_chunks_and_mark_ready(document.id, chunks, embeddings)

    with pytest.raises(DocumentNotIndexing):
        await repository.store_chunks_and_mark_ready(document.id, chunks[:1], embeddings[:1])

    assert len(await _locations(engine, document.id)) == 2


async def test_ingestion_ready_requires_indexing(
    repository: PostgresDocumentRepository, engine: AsyncEngine
) -> None:
    """DOM-02 in the adapter: a Ready update on a non-indexing document stores no chunks."""
    document, chunks, embeddings = await _indexed_input(repository)
    await repository.mark_failed(document.id, FailureReason.INDEXING_FAILED)

    with pytest.raises(DocumentNotIndexing):
        await repository.store_chunks_and_mark_ready(document.id, chunks, embeddings)

    stored = await repository.get(document.owner_id, document.id)
    assert stored is not None
    assert stored.status is DocumentStatus.FAILED
    assert await _locations(engine, document.id) == []


async def test_store_chunks_and_mark_ready_rejects_mismatched_embeddings(
    repository: PostgresDocumentRepository, engine: AsyncEngine
) -> None:
    document, chunks, embeddings = await _indexed_input(repository)

    with pytest.raises(ValueError, match="zip"):
        await repository.store_chunks_and_mark_ready(document.id, chunks, embeddings[:-1])

    stored = await repository.get(document.owner_id, document.id)
    assert stored is not None
    assert stored.status is DocumentStatus.INDEXING
    assert await _locations(engine, document.id) == []


async def test_mark_failed_records_the_reason(repository: PostgresDocumentRepository) -> None:
    document, _ = await repository.create_or_get(make_document())

    await repository.mark_failed(document.id, FailureReason.NO_EXTRACTABLE_TEXT)

    stored = await repository.get(document.owner_id, document.id)
    assert stored is not None
    assert stored.status is DocumentStatus.FAILED
    assert stored.failure_reason is FailureReason.NO_EXTRACTABLE_TEXT


@pytest.mark.parametrize("reason", sorted(RETRYABLE_FAILURES))
async def test_mark_indexing_clears_a_retryable_failure_reason(
    repository: PostgresDocumentRepository, reason: FailureReason
) -> None:
    document, _ = await repository.create_or_get(make_document())
    await repository.mark_failed(document.id, reason)

    retried = await repository.mark_indexing(document.id)

    assert retried is not None
    assert retried.status is DocumentStatus.INDEXING
    assert retried.failure_reason is None


async def test_mark_indexing_only_retries_a_retryable_failure(
    repository: PostgresDocumentRepository,
) -> None:
    document, chunks, embeddings = await _indexed_input(repository)
    await repository.store_chunks_and_mark_ready(document.id, chunks, embeddings)
    permanent, _ = await repository.create_or_get(make_document())
    await repository.mark_failed(permanent.id, FailureReason.NO_EXTRACTABLE_TEXT)

    assert await repository.mark_indexing(document.id) is None  # Ready: nothing to retry
    assert await repository.mark_indexing(permanent.id) is None  # depends on the file
    assert await repository.mark_indexing(uuid.uuid4()) is None


async def test_mark_indexing_concurrent_retries_have_a_single_winner(
    repository: PostgresDocumentRepository,
) -> None:
    document, _ = await repository.create_or_get(make_document())
    await repository.mark_failed(document.id, FailureReason.INDEXING_FAILED)

    first = await repository.mark_indexing(document.id)
    second = await repository.mark_indexing(document.id)

    assert first is not None
    assert second is None


async def test_mark_failed_never_overwrites_a_ready_document(
    repository: PostgresDocumentRepository,
) -> None:
    document, chunks, embeddings = await _indexed_input(repository)
    await repository.store_chunks_and_mark_ready(document.id, chunks, embeddings)

    await repository.mark_failed(document.id, FailureReason.INDEXING_FAILED)

    stored = await repository.get(document.owner_id, document.id)
    assert stored is not None
    assert stored.status is DocumentStatus.READY


async def test_fail_interrupted_indexing_fails_documents_left_indexing(
    repository: PostgresDocumentRepository,
) -> None:
    document, _ = await repository.create_or_get(make_document())

    count = await repository.fail_interrupted_indexing()

    stored = await repository.get(document.owner_id, document.id)
    assert count >= 1  # the session database also holds other tests' documents
    assert stored is not None
    assert stored.status is DocumentStatus.FAILED
    assert stored.failure_reason is FailureReason.INDEXING_FAILED


async def test_ingestion_parse_timeout_ends_failed(repository: PostgresDocumentRepository) -> None:
    """DOM-28: a PDF parse over the budget ends Failed in the database (fake parser, no wait)."""
    owner = uuid.uuid4()
    service = make_ingestion(
        repository,
        FakeEmbeddings(EMBEDDING_DIMENSIONS),
        parser=StalledParser(),
        pdf_parse_timeout_seconds=0.01,
    )
    content = fixture_bytes("expense-policy.pdf")
    result = await service.upload(owner, "expense-policy.pdf", content)

    await service.index(result.document, content)
    stored = await repository.get(owner, result.document.id)

    assert stored is not None
    assert stored.status is DocumentStatus.FAILED
    assert stored.failure_reason is FailureReason.PARSE_TIMEOUT
    assert stored.chunk_count == 0
