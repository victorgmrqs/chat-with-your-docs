"""Documents, chunks and the ingestion rules (DOM-01..06, DOM-25..26 in docs/domain-context.md)."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import PurePath

MAX_FILENAME_LENGTH = 255  # documents.filename column
MAX_SUFFIX_LENGTH = 10

ACCEPTED_FORMATS_HINT = "Upload a .pdf with selectable text, a .md or a .txt file."


class DocumentFormat(StrEnum):
    PDF = "pdf"
    MARKDOWN = "md"
    TEXT = "txt"


class DocumentStatus(StrEnum):
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class FailureReason(StrEnum):
    NO_EXTRACTABLE_TEXT = "no_extractable_text"  # permanent: depends on the file
    INDEXING_FAILED = "indexing_failed"  # transient: a re-upload indexes again
    PROVIDER_MISCONFIGURED = "provider_misconfigured"  # DOM-25: fixed by the operator, retryable
    TOO_MANY_PAGES = "too_many_pages"  # DOM-28: permanent, over PDF_MAX_PAGES
    PARSE_TIMEOUT = "parse_timeout"  # DOM-28: permanent, over PDF_PARSE_TIMEOUT_SECONDS


# DOM-04: failures that do not depend on the file; re-uploading the same file indexes it again.
RETRYABLE_FAILURES = frozenset(
    {FailureReason.INDEXING_FAILED, FailureReason.PROVIDER_MISCONFIGURED}
)


FAILURE_MESSAGES: dict[FailureReason, str] = {  # DOM-03: distinct, actionable messages
    FailureReason.NO_EXTRACTABLE_TEXT: (
        "No selectable text was found (for example a scanned PDF). "
        "Upload another version with selectable text."
    ),
    FailureReason.INDEXING_FAILED: (
        "Indexing failed for a temporary reason. Upload the same file again to retry."
    ),
    FailureReason.PROVIDER_MISCONFIGURED: (  # DOM-25
        "The embeddings provider rejected the configured API key or model. Ask the operator "
        "to check OPENAI_API_KEY and EMBEDDING_MODEL, then upload the same file again."
    ),
    FailureReason.TOO_MANY_PAGES: (  # DOM-28
        "The PDF has more pages than allowed. Split it into smaller files and upload those."
    ),
    FailureReason.PARSE_TIMEOUT: (  # DOM-28
        "Reading the PDF took too long. Save it again as a simpler PDF (for example with "
        "Print to PDF) or split it, then upload the new file."
    ),
}


class DomainError(Exception):
    """Base for business errors; `code` is the stable identifier exposed by the API."""

    code = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnsupportedFormat(DomainError):
    code = "unsupported_type"


class FileTooLarge(DomainError):
    code = "file_too_large"

    def __init__(self, limit_mb: int) -> None:
        super().__init__(f"The file is larger than {limit_mb} MB. Upload a smaller file.")


class EmptyFile(DomainError):
    code = "empty_file"


class DocumentNotFound(DomainError):
    code = "document_not_found"

    def __init__(self, message: str = "Document not found.") -> None:
        super().__init__(message)


class NoExtractableText(DomainError):
    code = FailureReason.NO_EXTRACTABLE_TEXT.value


class TooManyPages(DomainError):
    """DOM-28: the PDF has more pages than PDF_MAX_PAGES; raised before extracting text."""

    code = FailureReason.TOO_MANY_PAGES.value

    def __init__(self, pages: int, limit: int) -> None:
        super().__init__(f"{pages} pages, limit {limit}")
        self.pages = pages
        self.limit = limit


class ParseTimeout(DomainError):
    """DOM-28: parsing the PDF took longer than PDF_PARSE_TIMEOUT_SECONDS."""

    code = FailureReason.PARSE_TIMEOUT.value


class EmbeddingDimensionMismatch(DomainError):
    """DOM-26: EMBEDDING_DIMENSIONS differs from the database's vector column."""

    code = "embedding_dimension_mismatch"

    def __init__(self, configured: int, stored: int) -> None:
        super().__init__(
            "Uploads are unavailable: the embedding settings do not match the database. "
            "Ask the operator to check EMBEDDING_DIMENSIONS."
        )
        self.configured = configured
        self.stored = stored


@dataclass(frozen=True, slots=True)
class Document:
    id: uuid.UUID
    owner_id: uuid.UUID
    filename: str
    format: DocumentFormat
    sha256: str
    size_bytes: int
    status: DocumentStatus
    failure_reason: FailureReason | None
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    @property
    def failure_message(self) -> str | None:
        return FAILURE_MESSAGES[self.failure_reason] if self.failure_reason else None

    @property
    def can_retry(self) -> bool:
        """DOM-04: only failures that do not depend on the file are indexed again on re-upload."""

        return self.failure_reason in RETRYABLE_FAILURES


@dataclass(frozen=True, slots=True)
class Section:
    """A piece of extracted text and where it came from (page or heading path)."""

    text: str
    page: int | None = None
    heading: str | None = None


@dataclass(frozen=True, slots=True)
class Chunk:
    id: uuid.UUID
    document_id: uuid.UUID
    owner_id: uuid.UUID
    index: int
    text: str
    filename: str
    page: int | None
    heading: str | None

    @property
    def embedding_text(self) -> str:
        """DOM-05: provenance header for the embedding; `text` itself stays original."""

        location = f"Page {self.page}" if self.page else self.heading
        header = f"File: {self.filename}" + (f" | {location}" if location else "")

        return f"{header}\n\n{self.text}"


def build_chunks(document: Document, sections: list[Section]) -> list[Chunk]:
    """DOM-05: identity and provenance for each piece returned by the splitter."""
    return [
        Chunk(
            id=chunk_id(document.id, index),
            document_id=document.id,
            owner_id=document.owner_id,  # DOM-06
            index=index,
            text=section.text,
            filename=document.filename,
            page=section.page,
            heading=section.heading,
        )
        for index, section in enumerate(sections)
    ]


def chunk_id(document_id: uuid.UUID, index: int) -> uuid.UUID:
    """DOM-05: stable and unique across documents."""
    return uuid.uuid5(document_id, f"chunk:{index}")


def clean_filename(filename: str) -> str:
    """Keep only the base name: clients may send full or relative paths.

    Names longer than the 255-character column keep their extension (DOM-01).
    """
    name = PurePath(filename.replace("\\", "/")).name or "unnamed"
    if len(name) <= MAX_FILENAME_LENGTH:
        return name
    suffix = PurePath(name).suffix
    if len(suffix) > MAX_SUFFIX_LENGTH:  # not a real extension: plain truncation
        suffix = ""
    return name[: MAX_FILENAME_LENGTH - len(suffix)] + suffix


def detect_format(filename: str) -> DocumentFormat:
    """DOM-01: the extension decides the format; anything else is rejected with guidance."""

    suffix = PurePath(filename).suffix.lower().removeprefix(".")

    try:
        return DocumentFormat(suffix)
    except ValueError:
        shown = f".{suffix}" if suffix else "Files without an extension"
        raise UnsupportedFormat(f"{shown} is not supported. {ACCEPTED_FORMATS_HINT}") from None


def check_content(document_format: DocumentFormat, content: bytes) -> None:
    """DOM-01: the bytes must match the extension before anything is stored.

    A `.pdf` starts with `%PDF-`; a `.md` or `.txt` is valid UTF-8 without NUL bytes.
    Raises UnsupportedFormat otherwise.
    """
    if document_format is DocumentFormat.PDF:
        matches = content.startswith(b"%PDF-")
    else:
        matches = b"\x00" not in content and _is_utf8(content)
    if not matches:
        raise UnsupportedFormat(
            f"The file content does not match its .{document_format.value} extension. "
            f"{ACCEPTED_FORMATS_HINT}"
        )


def _is_utf8(content: bytes) -> bool:
    try:
        content.decode("utf-8")  # strict; a BOM is valid UTF-8 and the parser drops it
    except UnicodeDecodeError:
        return False
    return True
