import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Response, UploadFile, status
from pydantic import BaseModel

from app.api.dependencies import get_container
from app.api.errors import DATABASE_UNAVAILABLE, error_response
from app.composition import Container
from app.domain.documents import Document, DocumentFormat, DocumentStatus, FailureReason

router = APIRouter(tags=["documents"], prefix="/documents")


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    format: DocumentFormat
    size_bytes: int
    status: DocumentStatus
    failure_reason: FailureReason | None
    failure_message: str | None
    can_retry: bool  # DOM-04: uploading the same file again indexes it
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, document: Document) -> DocumentResponse:
        return cls(
            id=document.id,
            filename=document.filename,
            format=document.format,
            size_bytes=document.size_bytes,
            status=document.status,
            failure_reason=document.failure_reason,
            failure_message=document.failure_message,
            can_retry=document.can_retry,
            chunk_count=document.chunk_count,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_200_OK: {
            "model": DocumentResponse,
            "description": "Same file already uploaded: the existing document, not re-indexed",
        },
        status.HTTP_400_BAD_REQUEST: error_response("`empty_file`"),
        status.HTTP_413_CONTENT_TOO_LARGE: error_response(
            "`file_too_large` (MAX_UPLOAD_MB; a body over it plus 1 MB is cut off unread)"
        ),
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: error_response("`unsupported_type`"),
        status.HTTP_503_SERVICE_UNAVAILABLE: error_response(
            "`database_unavailable` or `embedding_dimension_mismatch`"
        ),
    },
)
async def upload_document(
    file: UploadFile,
    response: Response,
    background_tasks: BackgroundTasks,
    container: Annotated[Container, Depends(get_container)],
) -> DocumentResponse:
    """Register the file and index it in the background (202); poll GET /documents/{id}."""
    settings = container.settings
    # Read at most one byte past the limit: enough for the use case to reject it (DOM-01).
    content = await file.read(settings.max_upload_bytes + 1)
    result = await container.ingestion.upload(
        settings.default_owner_id, file.filename or "", content
    )
    if result.needs_indexing:
        background_tasks.add_task(container.ingestion.index, result.document, content)
    else:
        response.status_code = status.HTTP_200_OK
    return DocumentResponse.from_domain(result.document)


@router.get("", responses=DATABASE_UNAVAILABLE)
async def list_documents(
    container: Annotated[Container, Depends(get_container)],
) -> list[DocumentResponse]:
    """The owner's documents, newest first."""
    documents = await container.ingestion.list_for_owner(container.settings.default_owner_id)
    return [DocumentResponse.from_domain(document) for document in documents]


@router.get(
    "/{document_id}",
    responses={
        status.HTTP_404_NOT_FOUND: error_response("`document_not_found`"),
        **DATABASE_UNAVAILABLE,
    },
)
async def get_document(
    document_id: uuid.UUID,
    container: Annotated[Container, Depends(get_container)],
) -> DocumentResponse:
    """Status of one document (poll after upload until `ready` or `failed`)."""
    document = await container.ingestion.get(container.settings.default_owner_id, document_id)
    return DocumentResponse.from_domain(document)
