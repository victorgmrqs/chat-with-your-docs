"""Text extraction per format and chunk splitting (pypdf, LangChain text splitters)."""

import asyncio
import io
from collections.abc import Sequence
from dataclasses import replace

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.domain.documents import DocumentFormat, NoExtractableText, Section

_MARKDOWN_HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3"), ("####", "h4")]


class DocumentParserAdapter:
    """PDF per page (pypdf), Markdown per heading section, text as one section."""

    async def parse(self, content: bytes, document_format: DocumentFormat) -> list[Section]:
        parsed = await asyncio.to_thread(self._parse, content, document_format)
        sections = [s for s in map(_without_nul, parsed) if s.text]
        if not sections:
            raise NoExtractableText("no extractable text")  # DOM-03
        return sections

    def _parse(self, content: bytes, document_format: DocumentFormat) -> list[Section]:
        match document_format:
            case DocumentFormat.PDF:
                return _parse_pdf(content)
            case DocumentFormat.MARKDOWN:
                return _parse_markdown(_decode(content))
            case DocumentFormat.TEXT:
                text = _decode(content).strip()
                return [Section(text=text)] if text else []


def _without_nul(section: Section) -> Section:
    """PostgreSQL text cannot store NUL; left in, the insert fails on every retry (DOM-03)."""
    heading = section.heading.replace("\x00", "") if section.heading else section.heading
    return replace(section, text=section.text.replace("\x00", "").strip(), heading=heading)


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")  # -sig drops the BOM some Windows editors add
    except UnicodeDecodeError as exc:
        raise NoExtractableText("not valid UTF-8 text") from exc


def _parse_pdf(content: bytes) -> list[Section]:
    try:
        reader = PdfReader(io.BytesIO(content))
        pages = [(number, page.extract_text() or "") for number, page in enumerate(reader.pages, 1)]
    except Exception as exc:
        # pypdf raises PdfReadError but also ValueError, KeyError, struct.error... on malformed
        # files. Retrying cannot fix the file: permanent failure, not `indexing_failed` (DOM-03).
        raise NoExtractableText("unreadable PDF") from exc
    return [Section(text=text.strip(), page=number) for number, text in pages if text.strip()]


def _parse_markdown(text: str) -> list[Section]:
    splitter = MarkdownHeaderTextSplitter(_MARKDOWN_HEADERS, strip_headers=False)
    sections = []
    for piece in splitter.split_text(text):
        content = piece.page_content.strip()
        if not content:
            continue
        path = [str(piece.metadata[key]) for _, key in _MARKDOWN_HEADERS if key in piece.metadata]
        sections.append(Section(text=content, heading=" > ".join(path) or None))
    return sections


class RecursiveTextSplitter:
    """Chunk-sized pieces; a chunk never spans two pages or sections (DOM-05)."""

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    def split(self, sections: Sequence[Section]) -> list[Section]:
        return [
            Section(text=piece, page=section.page, heading=section.heading)
            for section in sections
            for piece in self._splitter.split_text(section.text)
            if piece.strip()
        ]
