import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.api.dependencies import get_container
from app.api.errors import DATABASE_UNAVAILABLE, error_response
from app.api.request_id import request_id_of
from app.composition import Container
from app.domain.answers import Answer, Passage, Source

router = APIRouter(tags=["chat"], prefix="/chat")


class ChatRequest(BaseModel):
    question: str  # length rules are domain rules (DOM-07): stable error codes


class PassageResponse(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page: int | None
    heading: str | None
    passage: str

    @classmethod
    def from_domain(cls, passage: Passage) -> PassageResponse:
        return cls(
            chunk_id=passage.chunk_id,
            document_id=passage.document_id,
            filename=passage.filename,
            page=passage.page,
            heading=passage.heading,
            passage=passage.text,
        )


class SourceResponse(PassageResponse):
    number: int  # the [n] marker in `answer`

    @classmethod
    def from_source(cls, source: Source) -> SourceResponse:
        passage = source.passage
        return cls(
            number=source.number,
            chunk_id=passage.chunk_id,
            document_id=passage.document_id,
            filename=passage.filename,
            page=passage.page,
            heading=passage.heading,
            passage=passage.text,
        )


class ChatResponse(BaseModel):
    request_id: uuid.UUID
    outcome: Literal["answered", "insufficient_evidence"]  # Outcome values
    answer: str  # [n] markers when answered; fixed message when insufficient (DOM-10)
    sources: list[SourceResponse]
    related_passage: PassageResponse | None  # no citation number (DOM-10)
    provider: str  # DOM-13
    model: str
    reranked: bool

    @classmethod
    def from_domain(cls, answer: Answer) -> ChatResponse:
        return cls(
            request_id=answer.request_id,
            outcome=answer.outcome.value,
            answer=answer.text,
            sources=[SourceResponse.from_source(source) for source in answer.sources],
            related_passage=(
                PassageResponse.from_domain(answer.related_passage)
                if answer.related_passage is not None
                else None
            ),
            provider=answer.provider,
            model=answer.model,
            reranked=answer.reranked,
        )


@router.post(
    "",
    responses={
        status.HTTP_400_BAD_REQUEST: error_response("`empty_question`, `question_too_long`"),
        status.HTTP_409_CONFLICT: error_response("`no_ready_documents`"),
        status.HTTP_502_BAD_GATEWAY: error_response(
            "`chat_unavailable`, `retrieval_unavailable` (technical failure, not evidence)"
        ),
        status.HTTP_504_GATEWAY_TIMEOUT: error_response("`chat_timeout`"),
        **DATABASE_UNAVAILABLE,
    },
)
async def ask(
    request: ChatRequest,
    container: Annotated[Container, Depends(get_container)],
    request_id: Annotated[uuid.UUID, Depends(request_id_of)],
) -> ChatResponse:
    """Answer from the owner's Ready documents with citations, or Not enough evidence."""
    answer = await container.answering.answer(
        container.settings.default_owner_id, request.question, request_id
    )
    return ChatResponse.from_domain(answer)
