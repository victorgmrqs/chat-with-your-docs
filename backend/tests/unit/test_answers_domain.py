import pytest

from app.domain.answers import clean_question, resolve_citations
from tests.factories import make_retrieved_chunk

APPROVAL = make_retrieved_chunk(filename="remote-work-policy.pdf", text="Requires approval.")
LIMIT = make_retrieved_chunk(filename="expense-policy.pdf", text="Limited to US$ 250.")
CONTEXT = {"S1": APPROVAL, "S2": LIMIT}


def test_resolve_citations_renumbers_by_first_appearance() -> None:
    resolved = resolve_citations("Limit is US$ 250 [S2]. Approval needed [S1].", CONTEXT)

    assert resolved.text == "Limit is US$ 250 [1]. Approval needed [2]."
    assert [(s.number, s.passage.chunk_id) for s in resolved.sources] == [
        (1, LIMIT.chunk_id),
        (2, APPROVAL.chunk_id),
    ]


def test_resolve_citations_same_label_twice_keeps_one_source() -> None:
    resolved = resolve_citations("A [S1]. B [S1, S1].", CONTEXT)

    assert resolved.text == "A [1]. B [1]."
    assert len(resolved.sources) == 1


def test_resolve_citations_semicolon_group() -> None:
    resolved = resolve_citations("Both apply [S1; S2].", CONTEXT)

    assert resolved.text == "Both apply [1][2]."


def test_clean_question_removes_control_characters() -> None:
    assert clean_question("  coworking\x00 limit\x07?\n") == "coworking limit?"


def test_clean_question_keeps_tabs_and_newlines_inside() -> None:
    assert clean_question("line one\nline\ttwo") == "line one\nline\ttwo"


def test_resolve_citations_grouped_marker() -> None:
    resolved = resolve_citations("Both apply [S1, S2].", CONTEXT)

    assert resolved.text == "Both apply [1][2]."


def test_resolve_citations_drops_invented_labels_and_markers() -> None:
    resolved = resolve_citations("Approval [S1]. Invented [S7]. Mixed [S9, S2].", CONTEXT)

    assert resolved.text == "Approval [1]. Invented. Mixed [2]."
    assert [s.passage.chunk_id for s in resolved.sources] == [APPROVAL.chunk_id, LIMIT.chunk_id]
    assert resolved.invalid_labels == 2


def test_resolve_citations_strips_model_numeric_markers() -> None:
    resolved = resolve_citations("Limit is US$ 250 [S2]. See footnote [3] and [1, 4].", CONTEXT)

    assert resolved.text == "Limit is US$ 250 [1]. See footnote and."
    assert [s.passage.chunk_id for s in resolved.sources] == [LIMIT.chunk_id]


def test_resolve_citations_numeric_markers_alone_leave_no_source() -> None:
    resolved = resolve_citations("Contractors get two weeks [1].", CONTEXT)

    assert resolved.sources == []
    assert resolved.text == "Contractors get two weeks."


def test_resolve_citations_only_invented_labels_leaves_no_source() -> None:
    resolved = resolve_citations("Unsupported claim [S3].", CONTEXT)

    assert resolved.sources == []
    assert resolved.invalid_labels == 1


def test_resolve_citations_source_keeps_provenance() -> None:
    [source] = resolve_citations("Approval [S1].", CONTEXT).sources

    assert (source.passage.filename, source.passage.page, source.passage.text) == (
        "remote-work-policy.pdf",
        2,
        "Requires approval.",
    )


@pytest.mark.parametrize(
    ("similarity", "fts_matched", "expected"),
    [(0.5, False, True), (0.1, True, True), (0.1, False, False), (0.3, False, True)],
)
def test_retrieved_chunk_is_evidence(similarity: float, fts_matched: bool, expected: bool) -> None:
    chunk = make_retrieved_chunk(similarity=similarity, fts_matched=fts_matched)

    assert chunk.is_evidence(min_relevance=0.3) is expected
