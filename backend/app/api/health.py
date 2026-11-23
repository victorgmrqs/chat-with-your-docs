from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.adapters.postgres_connection import DatabaseUnavailable
from app.api.dependencies import get_container
from app.composition import Container
from app.domain.documents import EmbeddingDimensionMismatch

router = APIRouter(tags=["health"], prefix="/health")


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    pgvector: str


class ErrorResponse(BaseModel):
    detail: str


@router.get("")
async def health() -> HealthResponse:
    """Liveness: the process is up. Never touches the database."""
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": (
                "`database unavailable`, `pgvector extension missing` or "
                "`embedding dimension mismatch`"
            ),
        }
    },
)
async def ready(container: Annotated[Container, Depends(get_container)]) -> ReadinessResponse:
    """Readiness: the database answers, pgvector is installed and the embedding column has
    the configured dimension (DOM-26)."""
    try:
        version = await container.readiness.pgvector_version()
        if version is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "pgvector extension missing")
        await container.ingestion.check_embedding_dimensions()
    except DatabaseUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "database unavailable") from exc
    except EmbeddingDimensionMismatch as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "embedding dimension mismatch"
        ) from exc
    return ReadinessResponse(status="ready", pgvector=version)
