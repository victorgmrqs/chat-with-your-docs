"""Hybrid retrieval in PostgreSQL: pgvector + full-text, fused with RRF (DOM-07, DOM-08)."""

import uuid
from collections.abc import Sequence

from pgvector.sqlalchemy import Vector
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.adapters.postgres_connection import database_connection
from app.domain.answers import RetrievedChunk
from app.domain.documents import DocumentStatus

RRF_K = 60  # standard Reciprocal Rank Fusion constant: damps the weight of the top ranks

# DOM-07: owner and Ready status are bound by the application in both branches.
# Full-text uses an OR of the question's lexemes: plainto_tsquery ANDs every term, which a
# natural-language question almost never matches; ts_rank_cd still favours chunks with more.
_HYBRID_SEARCH = text(
    """
    WITH query AS (
        SELECT
            CAST(:embedding AS vector) AS embedding,
            CAST(replace(plainto_tsquery('english', :query_text)::text, '&', '|') AS tsquery)
                AS terms
    ),
    vector_hits AS (
        SELECT id, row_number() OVER (ORDER BY distance) AS rank
        FROM (
            SELECT c.id, c.embedding <=> query.embedding AS distance
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            CROSS JOIN query
            WHERE c.owner_id = :owner_id AND d.status = :ready
            ORDER BY distance
            LIMIT :candidates
        ) nearest
    ),
    text_hits AS (
        SELECT id, row_number() OVER (ORDER BY relevance DESC) AS rank
        FROM (
            SELECT c.id, ts_rank_cd(c.search_vector, query.terms) AS relevance
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            CROSS JOIN query
            WHERE c.owner_id = :owner_id AND d.status = :ready
              AND c.search_vector @@ query.terms
            ORDER BY relevance DESC
            LIMIT :candidates
        ) matched
    ),
    fused AS (
        SELECT id, sum(1.0 / (:rrf_k + rank)) AS score
        FROM (SELECT id, rank FROM vector_hits UNION ALL SELECT id, rank FROM text_hits) ranks
        GROUP BY id
    )
    SELECT
        c.id AS chunk_id, c.document_id, d.filename, c.page, c.heading, c.text,
        fused.score,
        1 - (c.embedding <=> query.embedding) AS similarity,
        text_hits.id IS NOT NULL AS fts_matched
    FROM fused
    JOIN chunks c ON c.id = fused.id
    JOIN documents d ON d.id = c.document_id
    CROSS JOIN query
    LEFT JOIN text_hits ON text_hits.id = fused.id
    ORDER BY fused.score DESC, c.id
    LIMIT :limit
    """
).bindparams(bindparam("embedding", type_=Vector()))

_READY = DocumentStatus.READY.value

_HAS_READY = text(
    "SELECT EXISTS (SELECT 1 FROM documents WHERE owner_id = :owner_id AND status = :ready)"
)


class PostgresRetriever:
    """RetrieverPort: hybrid search in a single SQL statement."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def has_ready_documents(self, owner_id: uuid.UUID) -> bool:
        async with database_connection(self._engine) as connection:
            return bool(
                (
                    await connection.execute(_HAS_READY, {"owner_id": owner_id, "ready": _READY})
                ).scalar()
            )

    async def search(
        self,
        owner_id: uuid.UUID,
        query_text: str,
        query_embedding: Sequence[float],
        *,
        candidates: int,
        limit: int,
    ) -> list[RetrievedChunk]:
        parameters = {
            "owner_id": owner_id,
            "ready": _READY,
            "query_text": query_text,
            "embedding": list(query_embedding),
            "candidates": candidates,
            "limit": limit,
            "rrf_k": RRF_K,
        }
        async with database_connection(self._engine) as connection:
            rows = (await connection.execute(_HYBRID_SEARCH, parameters)).mappings().all()
        return [
            RetrievedChunk(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                filename=row["filename"],
                page=row["page"],
                heading=row["heading"],
                text=row["text"],
                score=float(row["score"]),
                similarity=float(row["similarity"]),
                fts_matched=bool(row["fts_matched"]),
            )
            for row in rows
        ]
