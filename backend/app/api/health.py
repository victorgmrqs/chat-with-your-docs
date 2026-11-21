from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.adapters.postgres_readiness import DatabaseUnavailable
from app.composition import Container

router = APIRouter(tags=["health"], prefix="/health")


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    pgvector: str


class ErrorResponse(BaseModel):
    detail: str


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


@router.get("")
async def health() -> HealthResponse:
    """Liveness: the process is up. Never touches the database."""
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "`database unavailable` or `pgvector extension missing`",
        }
    },
)
async def ready(container: Annotated[Container, Depends(get_container)]) -> ReadinessResponse:
    """Readiness: the database answers and pgvector is installed."""
    try:
        version = await container.readiness.pgvector_version()
    except DatabaseUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "database unavailable") from exc

    if version is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "pgvector extension missing")
    return ReadinessResponse(status="ready", pgvector=version)
