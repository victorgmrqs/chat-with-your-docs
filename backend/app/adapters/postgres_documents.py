"""Documents and chunks in PostgreSQL + pgvector (DOM-02, DOM-04, DOM-06)."""

import uuid
from collections.abc import Sequence

from pgvector.sqlalchemy import Vector
from sqlalchemy import RowMapping, column, delete, func, insert, select, table, update
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncEngine

from app.adapters.postgres_connection import database_connection
from app.application.ports import DocumentNotIndexing
from app.domain.documents import (
    RETRYABLE_FAILURES,
    Chunk,
    Document,
    DocumentFormat,
    DocumentStatus,
    FailureReason,
)

_documents = table(
    "documents",
    column("id"),
    column("owner_id"),
    column("filename"),
    column("format"),
    column("sha256"),
    column("size_bytes"),
    column("status"),
    column("failure_reason"),
    column("chunk_count"),
    column("created_at"),
    column("updated_at"),
)

_chunks = table(
    "chunks",
    column("id"),
    column("document_id"),
    column("owner_id"),
    column("chunk_index"),
    column("text"),
    column("page"),
    column("heading"),
    column("embedding", Vector()),  # binds list[float] as pgvector value
)


def _to_document(row: RowMapping) -> Document:
    reason = row["failure_reason"]
    return Document(
        id=row["id"],
        owner_id=row["owner_id"],
        filename=row["filename"],
        format=DocumentFormat(row["format"]),
        sha256=row["sha256"],
        size_bytes=row["size_bytes"],
        status=DocumentStatus(row["status"]),
        failure_reason=FailureReason(reason) if reason else None,
        chunk_count=row["chunk_count"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PostgresDocumentRepository:
    """DocumentRepository on SQLAlchemy Core (no ORM)."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def create_or_get(self, document: Document) -> tuple[Document, bool]:
        """DOM-04: one document per (owner, SHA-256); a duplicate returns the existing one."""
        insert = (
            postgresql.insert(_documents)
            .values(
                id=document.id,
                owner_id=document.owner_id,
                filename=document.filename,
                format=document.format.value,
                sha256=document.sha256,
                size_bytes=document.size_bytes,
                status=document.status.value,
                failure_reason=None,
                chunk_count=0,
                created_at=document.created_at,
                updated_at=document.updated_at,
            )
            .on_conflict_do_nothing(index_elements=["owner_id", "sha256"])
            .returning(*_documents.c)
        )
        existing = select(_documents).where(
            _documents.c.owner_id == document.owner_id,
            _documents.c.sha256 == document.sha256,
        )
        async with database_connection(self._engine, transaction=True) as connection:
            inserted = (await connection.execute(insert)).mappings().one_or_none()
            if inserted is not None:
                return _to_document(inserted), True
            return _to_document((await connection.execute(existing)).mappings().one()), False

    async def get(self, owner_id: uuid.UUID, document_id: uuid.UUID) -> Document | None:
        """DOM-06: another owner's document is indistinguishable from a missing one."""
        query = select(_documents).where(
            _documents.c.id == document_id,
            _documents.c.owner_id == owner_id,
        )
        async with database_connection(self._engine) as connection:
            row = (await connection.execute(query)).mappings().one_or_none()
        return _to_document(row) if row is not None else None

    async def list_for_owner(self, owner_id: uuid.UUID) -> list[Document]:
        """Newest first (index ix_documents_owner_created)."""
        query = (
            select(_documents)
            .where(_documents.c.owner_id == owner_id)
            .order_by(_documents.c.created_at.desc())
        )
        async with database_connection(self._engine) as connection:
            rows = (await connection.execute(query)).mappings().all()
        return [_to_document(row) for row in rows]

    async def mark_indexing(self, document_id: uuid.UUID) -> Document | None:
        """DOM-04 retry: only a retryable failure goes back to `indexing` (cleared reason).

        None when the document is not in that state, e.g. a concurrent upload already
        started the retry: exactly one caller wins, so one indexing job runs.
        """
        statement = (
            update(_documents)
            .where(
                _documents.c.id == document_id,
                _documents.c.status == DocumentStatus.FAILED.value,
                _documents.c.failure_reason.in_([reason.value for reason in RETRYABLE_FAILURES]),
            )
            .values(
                status=DocumentStatus.INDEXING.value,
                failure_reason=None,
                updated_at=func.now(),
            )
            .returning(*_documents.c)
        )
        async with database_connection(self._engine, transaction=True) as connection:
            row = (await connection.execute(statement)).mappings().one_or_none()
        return _to_document(row) if row is not None else None

    async def mark_failed(self, document_id: uuid.UUID, reason: FailureReason) -> None:
        """Only an `indexing` document fails: a Ready one is never overwritten (DOM-02)."""
        statement = (
            update(_documents)
            .where(
                _documents.c.id == document_id,
                _documents.c.status == DocumentStatus.INDEXING.value,
            )
            .values(
                status=DocumentStatus.FAILED.value,
                failure_reason=reason.value,
                updated_at=func.now(),
            )
        )
        async with database_connection(self._engine, transaction=True) as connection:
            await connection.execute(statement)

    async def store_chunks_and_mark_ready(
        self, document_id: uuid.UUID, chunks: Sequence[Chunk], embeddings: Sequence[list[float]]
    ) -> None:
        # Built before the transaction: a length mismatch raises ValueError before any write.
        rows = [
            {
                "id": chunk.id,
                "document_id": document_id,
                "owner_id": chunk.owner_id,  # DOM-06
                "chunk_index": chunk.index,
                "text": chunk.text,
                "page": chunk.page,
                "heading": chunk.heading,
                "embedding": embedding,
            }
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        mark_ready = (
            update(_documents)
            .where(
                _documents.c.id == document_id,
                _documents.c.status == DocumentStatus.INDEXING.value,  # DOM-02 state machine
            )
            .values(
                status=DocumentStatus.READY.value,
                failure_reason=None,
                chunk_count=len(rows),
                updated_at=func.now(),
            )
        )
        # DOM-02: chunks are replaced and the document becomes Ready in one transaction, and
        # only from `indexing`: the state is checked first, so a lost race writes no chunks.
        async with database_connection(self._engine, transaction=True) as connection:
            if (await connection.execute(mark_ready)).rowcount != 1:
                raise DocumentNotIndexing(str(document_id))  # rolls the transaction back
            await connection.execute(delete(_chunks).where(_chunks.c.document_id == document_id))
            if rows:  # an empty executemany would run a single insert without values
                await connection.execute(insert(_chunks), rows)

    async def fail_interrupted_indexing(self) -> int:
        """DOM-03: documents left `indexing` by a restart become `indexing_failed`."""
        statement = (
            update(_documents)
            .where(_documents.c.status == DocumentStatus.INDEXING.value)
            .values(
                status=DocumentStatus.FAILED.value,
                failure_reason=FailureReason.INDEXING_FAILED.value,
                updated_at=func.now(),
            )
        )
        async with database_connection(self._engine, transaction=True) as connection:
            result = await connection.execute(statement)
        return result.rowcount
