"""One handler maps every DomainError to its HTTP status and the {code, detail, request_id}
envelope; unexpected failures get the same envelope with a generic message (DOM-23)."""

import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.adapters.postgres_connection import DatabaseUnavailable
from app.api.request_id import REQUEST_ID_HEADER, request_id_of
from app.domain.answers import (
    ChatModelTimeout,
    ChatModelUnavailable,
    EmptyQuestion,
    NoReadyDocuments,
    QuestionTooLong,
    RetrievalUnavailable,
)
from app.domain.documents import (
    DocumentNotFound,
    DomainError,
    EmbeddingDimensionMismatch,
    EmptyFile,
    FileTooLarge,
    UnsupportedFormat,
)

STATUS_BY_ERROR: dict[type[DomainError], int] = {
    UnsupportedFormat: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    FileTooLarge: status.HTTP_413_CONTENT_TOO_LARGE,
    EmptyFile: status.HTTP_400_BAD_REQUEST,
    DocumentNotFound: status.HTTP_404_NOT_FOUND,
    EmbeddingDimensionMismatch: status.HTTP_503_SERVICE_UNAVAILABLE,  # DOM-26: operator fix
    EmptyQuestion: status.HTTP_400_BAD_REQUEST,
    QuestionTooLong: status.HTTP_400_BAD_REQUEST,
    NoReadyDocuments: status.HTTP_409_CONFLICT,
    # DOM-12: technical failures, never reported as insufficient evidence.
    ChatModelUnavailable: status.HTTP_502_BAD_GATEWAY,
    RetrievalUnavailable: status.HTTP_502_BAD_GATEWAY,
    ChatModelTimeout: status.HTTP_504_GATEWAY_TIMEOUT,
}


logger = logging.getLogger(__name__)

INTERNAL_ERROR_DETAIL = "Something went wrong on our side. Try again later."


class DomainErrorResponse(BaseModel):
    code: str  # stable identifier for clients (e.g. `unsupported_type`)
    detail: str  # user-facing message that says what to do instead
    request_id: uuid.UUID  # DOM-23: quote it when reporting a problem; finds the trace


def error_response(description: str) -> dict[str, object]:
    """OpenAPI entry for a documented DomainError status."""
    return {"model": DomainErrorResponse, "description": description}


DATABASE_UNAVAILABLE: dict[int | str, dict[str, object]] = {
    status.HTTP_503_SERVICE_UNAVAILABLE: error_response("`database_unavailable`")
}


def error_json(request: Request, code: str, detail: str, status_code: int) -> JSONResponse:
    """The {code, detail, request_id} envelope with the X-Request-ID header."""
    request_id = request_id_of(request)  # made here if the request-id middleware did not run
    body = DomainErrorResponse(code=code, detail=detail, request_id=request_id)
    return JSONResponse(
        body.model_dump(mode="json"),
        status_code=status_code,
        headers={REQUEST_ID_HEADER: str(request_id)},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
        status_code = STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST)
        return error_json(request, exc.code, exc.message, status_code)

    @app.exception_handler(DatabaseUnavailable)
    async def database_unavailable(request: Request, exc: DatabaseUnavailable) -> JSONResponse:
        # Short, stable text: never the driver message (backend-api rule).
        return error_json(
            request,
            "database_unavailable",
            "database unavailable",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        # Runs in Starlette's outermost middleware (after the request-id middleware): the
        # header is set here. The server still logs the traceback after this response.
        error_type, request_id = type(exc).__name__, str(request_id_of(request))
        logger.error(
            "Unhandled %s for request %s",
            error_type,
            request_id,
            extra={"request_id": request_id, "error_type": error_type},
        )
        return error_json(
            request, "internal_error", INTERNAL_ERROR_DETAIL, status.HTTP_500_INTERNAL_SERVER_ERROR
        )
