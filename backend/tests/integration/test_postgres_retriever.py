"""Hybrid retrieval against real PostgreSQL + pgvector (DOM-07, DOM-08)."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.adapters.postgres_documents import PostgresDocumentRepository
from app.adapters.postgres_retriever import PostgresRetriever
from app.application.ports import EmbeddingPort
from app.domain.documents import Document, Section, build_chunks
from tests.factories import EMBEDDING_DIMENSIONS, make_document
from tests.fakes import FakeEmbeddings, KeywordEmbeddings

pytestmark = pytest.mark.integration

APPROVAL = "Working from a coworking space requires prior manager approval."
LIMIT = "Coworking reimbursement is limited to US$ 250 per month per employee."
OFFICE = "The office opens at 8 a.m. and closes at 7 p.m. on business days."


@pytest.fixture
def retriever(engine: AsyncEngine) -> PostgresRetriever:
    return PostgresRetriever(engine)


async def _ready_document(
    repository: PostgresDocumentRepository,
    embeddings: EmbeddingPort,
    texts: list[str],
    **overrides: object,
) -> Document:
    document, _ = await repository.create_or_get(
        make_document(sha256=uuid.uuid4().hex * 2, **overrides)
    )
    chunks = build_chunks(document, [Section(text=t, page=i + 1) for i, t in enumerate(texts)])
    vectors = await embeddings.embed_documents([c.embedding_text for c in chunks])
    await repository.store_chunks_and_mark_ready(document.id, chunks, vectors)
    return document


async def test_rag_hybrid_exact_term(
    repository: PostgresDocumentRepository, retriever: PostgresRetriever
) -> None:
    # Hash-based vectors carry no meaning: only the full-text branch can find "US$ 250".
    embeddings = FakeEmbeddings(EMBEDDING_DIMENSIONS)
    owner = uuid.uuid4()
    await _ready_document(repository, embeddings, [APPROVAL, LIMIT, OFFICE], owner_id=owner)
    [query_vector] = await embeddings.embed_documents(["US$ 250"])

    results = await retriever.search(owner, "US$ 250", query_vector, candidates=20, limit=6)

    assert results[0].text == LIMIT
    assert results[0].fts_matched is True
    assert [r.text for r in results if r.fts_matched] == [LIMIT]


async def test_hybrid_search_natural_question_matches_any_term(
    repository: PostgresDocumentRepository, retriever: PostgresRetriever
) -> None:
    embeddings = FakeEmbeddings(EMBEDDING_DIMENSIONS)
    owner = uuid.uuid4()
    await _ready_document(repository, embeddings, [APPROVAL, LIMIT, OFFICE], owner_id=owner)
    question = "Do I need my manager's approval for coworking?"
    [query_vector] = await embeddings.embed_documents([question])

    results = await retriever.search(owner, question, query_vector, candidates=20, limit=6)

    matched = {r.text for r in results if r.fts_matched}
    assert matched == {APPROVAL, LIMIT}  # OR of lexemes; office hours share no term
    assert results[0].text == APPROVAL  # more matched terms rank higher


async def test_hybrid_search_reports_cosine_similarity(
    repository: PostgresDocumentRepository, retriever: PostgresRetriever
) -> None:
    embeddings = KeywordEmbeddings(EMBEDDING_DIMENSIONS)
    owner = uuid.uuid4()
    document = await _ready_document(repository, embeddings, [LIMIT, OFFICE], owner_id=owner)
    [query_vector] = await embeddings.embed_documents(
        [build_chunks(document, [Section(text=LIMIT, page=1)])[0].embedding_text]
    )

    results = await retriever.search(owner, "reimbursement", query_vector, candidates=20, limit=6)

    by_text = {r.text: r for r in results}
    assert by_text[LIMIT].similarity == pytest.approx(1.0, abs=1e-5)
    assert by_text[OFFICE].similarity < 0.5


async def test_hybrid_search_only_ready_documents_of_owner(
    engine: AsyncEngine, repository: PostgresDocumentRepository, retriever: PostgresRetriever
) -> None:
    embeddings = FakeEmbeddings(EMBEDDING_DIMENSIONS)
    owner = uuid.uuid4()
    mine = await _ready_document(repository, embeddings, [LIMIT], owner_id=owner)
    await _ready_document(repository, embeddings, [LIMIT], owner_id=uuid.uuid4())
    failed = await _ready_document(repository, embeddings, [LIMIT], owner_id=owner)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE documents SET status = 'failed', failure_reason = 'indexing_failed' "
                "WHERE id = :id"
            ),
            {"id": failed.id},
        )
    [query_vector] = await embeddings.embed_documents(["US$ 250"])

    results = await retriever.search(owner, "US$ 250", query_vector, candidates=20, limit=6)

    assert [r.document_id for r in results] == [mine.id]


async def test_hybrid_search_requires_document_owner_too(
    engine: AsyncEngine, repository: PostgresDocumentRepository, retriever: PostgresRetriever
) -> None:
    # DOM-06/07: a chunk whose owner disagrees with its document's owner is never returned.
    embeddings = FakeEmbeddings(EMBEDDING_DIMENSIONS)
    owner = uuid.uuid4()
    foreign = await _ready_document(repository, embeddings, [LIMIT], owner_id=uuid.uuid4())
    async with engine.begin() as connection:
        await connection.execute(
            text("UPDATE chunks SET owner_id = :owner WHERE document_id = :id"),
            {"owner": owner, "id": foreign.id},
        )
    [query_vector] = await embeddings.embed_documents(["US$ 250"])

    results = await retriever.search(owner, "US$ 250", query_vector, candidates=20, limit=6)

    assert results == []


async def test_hybrid_search_respects_limit(
    repository: PostgresDocumentRepository, retriever: PostgresRetriever
) -> None:
    embeddings = FakeEmbeddings(EMBEDDING_DIMENSIONS)
    owner = uuid.uuid4()
    await _ready_document(repository, embeddings, [APPROVAL, LIMIT, OFFICE], owner_id=owner)
    [query_vector] = await embeddings.embed_documents(["coworking"])

    results = await retriever.search(owner, "coworking", query_vector, candidates=20, limit=2)

    assert len(results) == 2
    assert results[0].score >= results[1].score


async def test_has_ready_documents(
    repository: PostgresDocumentRepository, retriever: PostgresRetriever
) -> None:
    owner = uuid.uuid4()
    assert await retriever.has_ready_documents(owner) is False

    await _ready_document(repository, FakeEmbeddings(EMBEDDING_DIMENSIONS), [LIMIT], owner_id=owner)

    assert await retriever.has_ready_documents(owner) is True
