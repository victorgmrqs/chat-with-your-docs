import asyncio
import threading
from typing import Any

import pytest
from pypdf import PageObject

from app.adapters import parsers
from app.adapters.parsers import DocumentParserAdapter, RecursiveTextSplitter
from app.domain.documents import DocumentFormat, NoExtractableText, Section, TooManyPages
from tests.factories import blank_pdf, fixture_bytes


async def test_parse_pdf_returns_one_section_per_page() -> None:
    sections = await DocumentParserAdapter(max_pdf_pages=500).parse(
        fixture_bytes("remote-work-policy.pdf"), DocumentFormat.PDF
    )

    assert [s.page for s in sections] == [1, 2]
    assert "prior manager approval" in sections[1].text


async def test_parse_markdown_returns_heading_paths() -> None:
    sections = await DocumentParserAdapter(max_pdf_pages=500).parse(
        fixture_bytes("parental-leave-policy.md"), DocumentFormat.MARKDOWN
    )

    by_heading = {s.heading: s.text for s in sections}
    full_time = "Parental Leave Policy > Eligibility > Full-time employees"
    assert "only to full-time employees" in by_heading[full_time]
    assert all(s.page is None for s in sections)


async def test_parse_text_returns_the_whole_file() -> None:
    sections = await DocumentParserAdapter(max_pdf_pages=500).parse(
        fixture_bytes("office-handbook.txt"), DocumentFormat.TEXT
    )

    assert len(sections) == 1
    assert sections[0].page is None
    assert sections[0].heading is None
    assert "reception desk" in sections[0].text


@pytest.mark.parametrize(
    ("content", "document_format"),
    [
        (fixture_bytes("scanned-notice.pdf"), DocumentFormat.PDF),
        (b"not a pdf at all", DocumentFormat.PDF),
        (fixture_bytes("expense-policy.pdf")[:600], DocumentFormat.PDF),
        (b"   \n\n ", DocumentFormat.TEXT),
        (b"\xff\xfe\x00binary", DocumentFormat.TEXT),
    ],
    ids=["scanned", "corrupt-pdf", "truncated-pdf", "blank-text", "not-utf8"],
)
async def test_parse_without_extractable_text_raises(
    content: bytes, document_format: DocumentFormat
) -> None:
    with pytest.raises(NoExtractableText):
        await DocumentParserAdapter(max_pdf_pages=500).parse(content, document_format)


def test_splitter_keeps_page_and_heading_on_every_piece() -> None:
    splitter = RecursiveTextSplitter(chunk_size=40, chunk_overlap=10)
    long_text = "Coworking reimbursement is limited. " * 5

    pieces = splitter.split([Section(text=long_text, page=2), Section(text="Short", heading="H")])

    assert len(pieces) > 2
    assert all(len(p.text) <= 40 for p in pieces)
    assert {p.page for p in pieces[:-1]} == {2}
    assert pieces[-1] == Section(text="Short", heading="H")


async def test_parse_text_with_nul_bytes_strips_them() -> None:
    sections = await DocumentParserAdapter(max_pdf_pages=500).parse(
        b"Reception\x00 desk", DocumentFormat.TEXT
    )

    assert sections == [Section(text="Reception desk")]


async def test_parse_pdf_over_the_page_limit_raises_too_many_pages() -> None:
    with pytest.raises(TooManyPages) as raised:
        await DocumentParserAdapter(max_pdf_pages=3).parse(blank_pdf(4), DocumentFormat.PDF)

    assert (raised.value.pages, raised.value.limit) == (4, 3)


async def test_parse_pdf_at_the_page_limit_is_parsed() -> None:
    sections = await DocumentParserAdapter(max_pdf_pages=2).parse(
        fixture_bytes("expense-policy.pdf"), DocumentFormat.PDF
    )

    assert [s.page for s in sections] == [1, 2]


async def test_parse_pdf_cancelled_stops_before_the_next_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOM-28: the timeout cancels the parse; the worker thread stops at its next page."""
    in_page, release, finished = threading.Event(), threading.Event(), threading.Event()
    pages_read: list[int] = []

    def blocking_extract(page: PageObject, *args: Any, **kwargs: Any) -> str:
        pages_read.append(1)
        in_page.set()
        release.wait(5)  # held until the parse has been cancelled
        return "text"

    real_parse_pdf = parsers._parse_pdf

    def tracked_parse_pdf(*args: Any) -> list[Section]:
        try:
            return real_parse_pdf(*args)
        finally:
            finished.set()

    monkeypatch.setattr(PageObject, "extract_text", blocking_extract)
    monkeypatch.setattr(parsers, "_parse_pdf", tracked_parse_pdf)
    parse = asyncio.create_task(
        DocumentParserAdapter(max_pdf_pages=500).parse(blank_pdf(3), DocumentFormat.PDF)
    )
    await asyncio.to_thread(in_page.wait, 5)

    parse.cancel()
    with pytest.raises(asyncio.CancelledError):
        await parse
    release.set()
    await asyncio.to_thread(finished.wait, 5)

    assert finished.is_set()
    assert len(pages_read) == 1  # pages 2 and 3 were never read
