"""AnswerQuestion with declared fakes (no I/O). Scenario names follow CWYD-4."""

import logging
import uuid
from collections.abc import Sequence

import pytest

from app.application.answering import AnswerQuestion
from app.application.prompts import AnswerDraft, RerankDraft
from app.domain.answers import (
    INSUFFICIENT_EVIDENCE_MESSAGE,
    ChatModelTimeout,
    ChatModelUnavailable,
    EmptyQuestion,
    NoReadyDocuments,
    Outcome,
    QuestionTooLong,
    RetrievalUnavailable,
    RetrievedChunk,
)
from tests.factories import ANSWERING_LIMITS, make_answering, make_retrieved_chunk
from tests.fakes import FailingEmbeddings, FakeChatModel, FakeEmbeddings, FakeRetriever, Reply

OWNER = uuid.uuid4()
COWORKING = "Can I work from a coworking space, and what is the monthly limit?"
CONTRACTORS = "What is the parental leave policy for contractors?"

APPROVAL = make_retrieved_chunk(
    filename="remote-work-policy.pdf",
    page=2,
    text="Working from a coworking space requires prior manager approval.",
)
LIMIT = make_retrieved_chunk(
    filename="expense-policy.pdf",
    page=2,
    text="Coworking reimbursement is limited to US$ 250 per month per employee.",
)
FULL_TIME_ONLY = make_retrieved_chunk(
    filename="parental-leave-policy.md",
    page=None,
    heading="Parental Leave Policy > Eligibility > Full-time employees",
    text="Parental leave applies only to full-time employees with at least six months of service.",
)

LIMITS = ANSWERING_LIMITS


def _use_case(
    chunks: Sequence[RetrievedChunk],
    *replies: Reply,
    rerank: bool = False,
    has_ready: bool = True,
) -> tuple[AnswerQuestion, FakeChatModel]:
    chat = FakeChatModel(*replies)
    use_case = make_answering(
        FakeRetriever(chunks, has_ready=has_ready), FakeEmbeddings(8), chat, rerank=rerank
    )
    return use_case, chat


def _answered(text: str) -> AnswerDraft:
    return AnswerDraft(outcome="answered", answer=text, closest_source_id=None)


async def test_rag_answer_success() -> None:
    use_case, _ = _use_case(
        [APPROVAL, LIMIT],
        _answered("Yes, with prior manager approval [S1]. The limit is US$ 250 per month [S2]."),
    )

    answer = await use_case.answer(OWNER, COWORKING)

    assert answer.outcome is Outcome.ANSWERED
    assert (
        answer.text == "Yes, with prior manager approval [1]. The limit is US$ 250 per month [2]."
    )
    assert [
        (s.number, s.passage.filename, s.passage.page, s.passage.text) for s in answer.sources
    ] == [
        (1, "remote-work-policy.pdf", 2, APPROVAL.text),
        (2, "expense-policy.pdf", 2, LIMIT.text),
    ]
    assert (answer.provider, answer.model, answer.reranked) == ("fake", "fake-chat-model", False)


async def test_rag_answer_insufficient_evidence() -> None:
    use_case, _ = _use_case(
        [FULL_TIME_ONLY],
        AnswerDraft(outcome="insufficient_evidence", answer="", closest_source_id="S1"),
    )

    answer = await use_case.answer(OWNER, CONTRACTORS)

    assert answer.outcome is Outcome.INSUFFICIENT_EVIDENCE
    assert answer.text == INSUFFICIENT_EVIDENCE_MESSAGE
    assert answer.sources == []
    assert answer.related_passage is not None
    assert answer.related_passage.chunk_id == FULL_TIME_ONLY.chunk_id


async def test_rag_answer_insufficient_evidence_ignores_model_text() -> None:
    use_case, _ = _use_case(
        [FULL_TIME_ONLY],
        AnswerDraft(
            outcome="insufficient_evidence",
            answer="Contractors get 2 weeks.",
            closest_source_id=None,
        ),
    )

    answer = await use_case.answer(OWNER, CONTRACTORS)

    assert answer.text == INSUFFICIENT_EVIDENCE_MESSAGE
    assert answer.related_passage is None


async def test_rag_answer_invalid_citation() -> None:
    use_case, _ = _use_case([APPROVAL, LIMIT], _answered("Contractors get 2 weeks [S7]."))

    answer = await use_case.answer(OWNER, CONTRACTORS)

    assert answer.outcome is Outcome.INSUFFICIENT_EVIDENCE
    assert answer.sources == []
    assert answer.text == INSUFFICIENT_EVIDENCE_MESSAGE


async def test_rag_answer_invalid_citation_mixed_keeps_valid_sources() -> None:
    use_case, _ = _use_case([APPROVAL, LIMIT], _answered("Approval [S1]. Unsupported [S5]."))

    answer = await use_case.answer(OWNER, COWORKING)

    assert answer.outcome is Outcome.ANSWERED
    assert answer.text == "Approval [1]. Unsupported."
    assert [s.passage.chunk_id for s in answer.sources] == [APPROVAL.chunk_id]


async def test_rag_answer_invalid_citation_unknown_closest_source_dropped() -> None:
    use_case, _ = _use_case(
        [FULL_TIME_ONLY],
        AnswerDraft(outcome="insufficient_evidence", answer="", closest_source_id="S42"),
    )

    answer = await use_case.answer(OWNER, CONTRACTORS)

    assert answer.related_passage is None


async def test_rag_answer_provider_timeout() -> None:
    use_case, _ = _use_case([APPROVAL, LIMIT], ChatModelTimeout())

    with pytest.raises(ChatModelTimeout):
        await use_case.answer(OWNER, COWORKING)


async def test_rag_answer_provider_unavailable() -> None:
    use_case, _ = _use_case([APPROVAL, LIMIT], ChatModelUnavailable())

    with pytest.raises(ChatModelUnavailable):
        await use_case.answer(OWNER, COWORKING)


async def test_answer_question_embeddings_down_is_technical_failure() -> None:
    use_case = AnswerQuestion(FakeRetriever([LIMIT]), FailingEmbeddings(), FakeChatModel(), LIMITS)

    with pytest.raises(RetrievalUnavailable):
        await use_case.answer(OWNER, COWORKING)


async def test_answer_question_no_evidence_skips_chat_model() -> None:
    weak = make_retrieved_chunk(similarity=0.1, fts_matched=False)
    use_case, chat = _use_case([weak])

    answer = await use_case.answer(OWNER, CONTRACTORS)

    assert answer.outcome is Outcome.INSUFFICIENT_EVIDENCE
    assert answer.related_passage is None
    assert chat.prompts == []


async def test_answer_question_only_evidence_reaches_prompt() -> None:
    weak = make_retrieved_chunk(text="Office opens at 8 a.m.", similarity=0.1, fts_matched=False)
    use_case, chat = _use_case([LIMIT, weak], _answered("Limit [S1]."))

    await use_case.answer(OWNER, COWORKING)

    assert LIMIT.text in chat.prompts[0].user
    assert weak.text not in chat.prompts[0].user


async def test_answer_question_reranker_on_only_reranked_chunks_reach_prompt() -> None:
    use_case, chat = _use_case(
        [APPROVAL, LIMIT],
        RerankDraft(source_ids=["S2", "S1"]),  # rerank_top_n=1 keeps LIMIT only
        _answered("The limit is US$ 250 [S1]."),
        rerank=True,
    )

    answer = await use_case.answer(OWNER, COWORKING)

    answer_prompt = chat.prompts[1].user
    assert LIMIT.text in answer_prompt
    assert APPROVAL.text not in answer_prompt
    assert [s.passage.chunk_id for s in answer.sources] == [LIMIT.chunk_id]
    assert answer.reranked is True


async def test_answer_question_reranker_off_uses_fused_order() -> None:
    use_case, chat = _use_case([APPROVAL, LIMIT], _answered("A [S1]. B [S2]."))

    answer = await use_case.answer(OWNER, COWORKING)

    assert len(chat.prompts) == 1
    assert chat.prompts[0].user.index(APPROVAL.text) < chat.prompts[0].user.index(LIMIT.text)
    assert answer.reranked is False


async def test_answer_question_reranker_failure_fails_open() -> None:
    use_case, chat = _use_case(
        [APPROVAL, LIMIT], ChatModelTimeout(), _answered("A [S1]. B [S2]."), rerank=True
    )

    answer = await use_case.answer(OWNER, COWORKING)

    assert answer.reranked is False
    assert APPROVAL.text in chat.prompts[1].user
    assert LIMIT.text in chat.prompts[1].user


@pytest.mark.parametrize("source_ids", [["S9"], []])
async def test_answer_question_reranker_keeps_nothing_fails_open(source_ids: list[str]) -> None:
    # DOM-11: invented or no ids are a reranker failure; the fused evidence reaches the prompt.
    use_case, chat = _use_case(
        [APPROVAL, LIMIT],
        RerankDraft(source_ids=source_ids),
        _answered("A [S1]. B [S2]."),
        rerank=True,
    )

    answer = await use_case.answer(OWNER, COWORKING)

    assert answer.outcome is Outcome.ANSWERED
    assert [s.passage.chunk_id for s in answer.sources] == [APPROVAL.chunk_id, LIMIT.chunk_id]
    assert answer.reranked is False
    assert len(chat.prompts) == 2


@pytest.mark.parametrize("question", ["", "   \n", "\x00\x01"])
async def test_answer_question_empty_question(question: str) -> None:
    use_case, _ = _use_case([LIMIT])

    with pytest.raises(EmptyQuestion):
        await use_case.answer(OWNER, question)


async def test_answer_question_too_long() -> None:
    use_case, _ = _use_case([LIMIT])

    with pytest.raises(QuestionTooLong):
        await use_case.answer(OWNER, "x" * 201)


async def test_answer_question_no_ready_documents() -> None:
    use_case, _ = _use_case([], has_ready=False)

    with pytest.raises(NoReadyDocuments):
        await use_case.answer(OWNER, COWORKING)


async def test_answer_question_log_has_no_content(caplog: pytest.LogCaptureFixture) -> None:
    use_case, _ = _use_case([APPROVAL, LIMIT], _answered("Needs approval [S1]."))

    with caplog.at_level(logging.INFO, logger="app.application.answering"):
        await use_case.answer(OWNER, COWORKING)

    [record] = caplog.records
    logged = record.getMessage() + repr(record.__dict__)
    assert COWORKING not in logged
    assert "Needs approval" not in logged
    assert APPROVAL.text not in logged
    assert (record.__dict__["provider"], record.__dict__["outcome"]) == ("fake", "answered")


async def test_answer_question_unexpected_failure_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class BrokenRetriever(FakeRetriever):
        async def search(self, *args: object, **kwargs: object) -> list[RetrievedChunk]:
            raise ConnectionError("database down")

    use_case = AnswerQuestion(BrokenRetriever(), FakeEmbeddings(8), FakeChatModel(), LIMITS)

    with (
        caplog.at_level(logging.INFO, logger="app.application.answering"),
        pytest.raises(ConnectionError),
    ):
        await use_case.answer(OWNER, COWORKING)

    [record] = caplog.records
    assert (record.__dict__["outcome"], record.__dict__["error_type"]) == (
        "error",
        "ConnectionError",
    )
