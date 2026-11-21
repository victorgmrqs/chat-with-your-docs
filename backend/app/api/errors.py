"""One handler maps every DomainError to its HTTP status and the {code, detail} envelope."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.adapters.postgres_connection import DatabaseUnavailable
from app.domain.documents import (
    DocumentNotFound,
    DomainError,
    EmptyFile,
    FileTooLarge,
    UnsupportedFormat,
)

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    UnsupportedFormat: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    FileTooLarge: status.HTTP_413_CONTENT_TOO_LARGE,
    EmptyFile: status.HTTP_400_BAD_REQUEST,
    DocumentNotFound: status.HTTP_404_NOT_FOUND,
}


class DomainErrorResponse(BaseModel):
    code: str  # stable identifier for clients (e.g. `unsupported_type`)
    detail: str  # user-facing message that says what to do instead


def error_response(description: str) -> dict[str, object]:
    """OpenAPI entry for a documented DomainError status."""
    return {"model": DomainErrorResponse, "description": description}


DATABASE_UNAVAILABLE: dict[int | str, dict[str, object]] = {
    status.HTTP_503_SERVICE_UNAVAILABLE: error_response("`database_unavailable`")
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
        body = DomainErrorResponse(code=exc.code, detail=exc.message)
        return JSONResponse(
            body.model_dump(),
            status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        )

    @app.exception_handler(DatabaseUnavailable)
    async def database_unavailable(request: Request, exc: DatabaseUnavailable) -> JSONResponse:
        # Short, stable text: never the driver message (backend-api rule).
        body = DomainErrorResponse(code="database_unavailable", detail="database unavailable")
        return JSONResponse(body.model_dump(), status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
