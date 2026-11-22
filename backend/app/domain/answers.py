"""Answers, citations and the answering rules (DOM-07..13 in docs/domain-context.md)."""

import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from app.domain.documents import DomainError

# DOM-10: written by the backend, never by the model.
INSUFFICIENT_EVIDENCE_MESSAGE = (
    "Not enough evidence in your documents to answer this question. "
    "Rephrase the question or upload a document that covers it."
)

# One marker group: [S1] or [S1, S3]. Labels are the ones given in the prompt (DOM-09).
_MARKER = re.compile(r"(\s*)\[(S\d+(?:\s*[,;]\s*S\d+)*)\]")
# Numeric markers written by the model ([3], [1, 2]) would look like backend citations.
_NUMERIC_MARKER = re.compile(r"\s*\[\d+(?:\s*[,;]\s*\d+)*\]")


# C0 control characters except tab, newline and carriage return (PostgreSQL rejects NUL).
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_question(question: str) -> str:
    """DOM-07: control characters are removed and surrounding whitespace trimmed."""
    return _CONTROL_CHARACTERS.sub("", question).strip()


class Outcome(StrEnum):
    ANSWERED = "answered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EmptyQuestion(DomainError):
    code = "empty_question"

    def __init__(self) -> None:
        super().__init__("The question is empty. Type a question about your documents.")


class QuestionTooLong(DomainError):
    code = "question_too_long"

    def __init__(self, max_chars: int) -> None:
        super().__init__(f"The question is longer than {max_chars} characters. Shorten it.")


class NoReadyDocuments(DomainError):
    code = "no_ready_documents"

    def __init__(self) -> None:
        super().__init__("No document is ready yet. Upload a document and wait until it is Ready.")


class ChatModelTimeout(DomainError):
    """DOM-12: the chat provider did not answer in time (technical failure)."""

    code = "chat_timeout"

    def __init__(self) -> None:
        super().__init__("The answer took too long. Your question was kept: try again.")


class ChatModelUnavailable(DomainError):
    """DOM-12: provider error or invalid structured output after the adapter's retries."""

    code = "chat_unavailable"

    def __init__(self) -> None:
        super().__init__("The answer could not be generated. Try again in a moment.")


class RetrievalUnavailable(DomainError):
    """DOM-12: the question could not be embedded (embeddings provider down)."""

    code = "retrieval_unavailable"

    def __init__(self) -> None:
        super().__init__("Your documents could not be searched right now. Try again in a moment.")


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A chunk returned by hybrid retrieval, with the signals the relevance gate needs."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page: int | None
    heading: str | None
    text: str
    score: float  # fused RRF score: ordering only, not a relevance measure
    similarity: float  # cosine similarity to the question
    fts_matched: bool  # matched the full-text branch

    def is_evidence(self, min_relevance: float) -> bool:
        """DOM-08: close enough in meaning, or it contains the question's exact terms."""
        return self.fts_matched or self.similarity >= min_relevance


@dataclass(frozen=True, slots=True)
class Passage:
    """Provenance of a cited (or related) chunk, as stored at ingestion (DOM-05)."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page: int | None
    heading: str | None
    text: str

    @classmethod
    def from_chunk(cls, chunk: RetrievedChunk) -> Passage:
        return cls(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            filename=chunk.filename,
            page=chunk.page,
            heading=chunk.heading,
            text=chunk.text,
        )


@dataclass(frozen=True, slots=True)
class Source:
    number: int  # the [n] marker in the answer text
    passage: Passage


@dataclass(frozen=True, slots=True)
class Answer:
    request_id: uuid.UUID
    outcome: Outcome
    text: str
    sources: list[Source]
    related_passage: Passage | None  # DOM-10: shown without a citation number
    provider: str  # DOM-13
    model: str
    reranked: bool


@dataclass(frozen=True, slots=True)
class ResolvedCitations:
    text: str
    sources: list[Source]
    invalid_labels: int  # cited labels that were not in the prompt (dropped)


def resolve_citations(text: str, context: Mapping[str, RetrievedChunk]) -> ResolvedCitations:
    """DOM-09: keep labels that were in the prompt, renumber them 1..n by first appearance.

    Invented labels and model-written numeric markers are dropped; the text is otherwise
    unchanged.
    """
    numbers: dict[str, int] = {}
    invalid = 0

    def renumber(match: re.Match[str]) -> str:
        nonlocal invalid
        labels = [label.strip() for label in re.split(r"[,;]", match.group(2))]
        kept: list[int] = []
        for label in labels:
            if label not in context:
                invalid += 1
                continue
            number = numbers.setdefault(label, len(numbers) + 1)
            if number not in kept:
                kept.append(number)
        if not kept:
            return ""
        return match.group(1) + "".join(f"[{number}]" for number in kept)

    # DOM-09: drop model-written [n] first, so every [n] in the result is a backend citation.
    resolved = _MARKER.sub(renumber, _NUMERIC_MARKER.sub("", text)).strip()
    sources = [
        Source(number=number, passage=Passage.from_chunk(context[label]))
        for label, number in numbers.items()
    ]
    return ResolvedCitations(text=resolved, sources=sources, invalid_labels=invalid)
