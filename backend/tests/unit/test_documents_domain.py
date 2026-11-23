import uuid

import pytest

from app.domain.documents import (
    DocumentFormat,
    DocumentStatus,
    FailureReason,
    Section,
    UnsupportedFormat,
    build_chunks,
    check_content,
    chunk_id,
    clean_filename,
    detect_format,
)
from tests.factories import make_document


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("remote-work-policy.pdf", DocumentFormat.PDF),
        ("parental-leave-policy.md", DocumentFormat.MARKDOWN),
        ("office-handbook.txt", DocumentFormat.TEXT),
        ("README.MD", DocumentFormat.MARKDOWN),  # extension is case-insensitive
    ],
)
def test_detect_format_accepts_pdf_markdown_and_text(
    filename: str, expected: DocumentFormat
) -> None:
    assert detect_format(filename) is expected


@pytest.mark.parametrize("filename", ["unsupported.docx", "image.png", "no-extension"])
def test_detect_format_rejects_other_types_with_guidance(filename: str) -> None:
    with pytest.raises(UnsupportedFormat) as exec_info:
        detect_format(filename)

    assert exec_info.value.code == "unsupported_type"
    assert ".pdf" in exec_info.value.message


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("expense-policy.pdf", "expense-policy.pdf"),
        ("C:\\Users\\me\\expense-policy.pdf", "expense-policy.pdf"),
        ("../../etc/expense-policy.pdf", "expense-policy.pdf"),
        ("/home/me/uploads/expense-policy.pdf", "expense-policy.pdf"),
        ("", "unnamed"),
        ("a" * 300 + ".pdf", "a" * 251 + ".pdf"),
        ("a." + "b" * 300, ("a." + "b" * 300)[:255]),
    ],
    ids=["plain", "windows-path", "traversal", "posix-path", "empty", "too-long", "no-extension"],
)
def test_clean_filename_drops_client_paths(filename: str, expected: str) -> None:
    assert clean_filename(filename) == expected


def test_chunk_id_is_stable_and_unique_per_document() -> None:
    first_document, second_document = uuid.uuid4(), uuid.uuid4()

    assert chunk_id(first_document, 0) == chunk_id(first_document, 0)
    assert chunk_id(first_document, 0) != chunk_id(first_document, 1)
    assert chunk_id(first_document, 0) != chunk_id(second_document, 0)


@pytest.mark.parametrize(
    ("status", "failure_reason", "expected"),
    [
        (DocumentStatus.FAILED, FailureReason.INDEXING_FAILED, True),
        (DocumentStatus.FAILED, FailureReason.NO_EXTRACTABLE_TEXT, False),
        (DocumentStatus.READY, None, False),
        (DocumentStatus.INDEXING, None, False),
    ],
    ids=["transient-failure", "permanent-failure", "ready", "indexing"],
)
def test_document_can_retry_only_after_a_transient_failure(
    status: DocumentStatus, failure_reason: FailureReason | None, expected: bool
) -> None:
    document = make_document(status=status, failure_reason=failure_reason)

    assert document.can_retry is expected


def test_chunk_embedding_text_has_provenance_header_and_keeps_original_text() -> None:
    document = make_document(filename="expense-policy.pdf")
    sections = [
        Section(text="Coworking reimbursement is limited to US$ 250.", page=2),
        Section(text="Applies only to full-time employees.", heading="Eligibility > Full-time"),
        Section(text="The office opens at 8 a.m."),
    ]

    chunks = build_chunks(document, sections)

    assert [c.id for c in chunks] == [chunk_id(document.id, i) for i in range(3)]
    assert all(c.owner_id == document.owner_id for c in chunks)
    assert chunks[0].text == "Coworking reimbursement is limited to US$ 250."
    assert chunks[0].embedding_text == (
        "File: expense-policy.pdf | Page 2\n\nCoworking reimbursement is limited to US$ 250."
    )
    assert chunks[1].embedding_text.startswith(
        "File: expense-policy.pdf | Eligibility > Full-time\n\n"
    )
    assert chunks[1].embedding_text.startswith(
        "File: expense-policy.pdf | Eligibility > Full-time\n\n"
    )


def test_clean_filename_long_name_keeps_a_supported_extension() -> None:
    name = clean_filename("a" * 300 + ".pdf")

    assert len(name) == 255
    assert detect_format(name) is DocumentFormat.PDF


@pytest.mark.parametrize(
    ("document_format", "content"),
    [
        (DocumentFormat.PDF, b"%PDF-1.7\n..."),
        (DocumentFormat.TEXT, "Café opens at 8.".encode()),
        (DocumentFormat.MARKDOWN, b"\xef\xbb\xbf# Title\n"),  # BOM: valid UTF-8
    ],
    ids=["pdf", "utf8-text", "markdown-with-bom"],
)
def test_check_content_accepts_matching_content(
    document_format: DocumentFormat, content: bytes
) -> None:
    check_content(document_format, content)  # DOM-01: no exception


@pytest.mark.parametrize(
    ("document_format", "content"),
    [
        (DocumentFormat.PDF, b"\x89PNG\r\n\x1a\n renamed image"),
        (DocumentFormat.PDF, b" %PDF-1.7"),  # must start with the header
        (DocumentFormat.TEXT, b"caf\xe9 latin-1"),
        (DocumentFormat.TEXT, b"MZ\x90\x00 executable"),
        (DocumentFormat.MARKDOWN, b"# Title\x00"),
    ],
    ids=["renamed-image", "pdf-header-not-first", "invalid-utf8", "binary", "nul-byte"],
)
def test_check_content_rejects_content_that_does_not_match(
    document_format: DocumentFormat, content: bytes
) -> None:
    with pytest.raises(UnsupportedFormat, match=rf"does not match its \.{document_format.value}"):
        check_content(document_format, content)
