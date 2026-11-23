"""Traces of the chat and ingestion pipelines (CWYD-12, DOM-22..24), read from an in-memory
exporter. Required scenarios: otel_chat_trace_success, otel_no_content_by_default,
otel_provider_error_recorded."""

import uuid
from collections.abc import Mapping, Sequence

import pytest
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from opentelemetry.util.types import AttributeValue

from app.application import telemetry as t
from app.application.answering import AnswerQuestion
from app.application.prompts import AnswerDraft, RerankDraft
from app.domain.answers import ChatModelUnavailable, RetrievedChunk
from app.domain.documents import DocumentStatus, FailureReason
from app.domain.usage import ModelPrice, PriceTable
from tests.factories import fixture_bytes, make_answering, make_ingestion, make_retrieved_chunk
from tests.fakes import (
    FailingEmbeddings,
    FakeChatModel,
    FakeEmbeddings,
    FakeRetriever,
    InMemoryDocumentRepository,
    Reply,
)

OWNER = uuid.UUID("00000000-0000-0000-0000-000000000001")
REQUEST_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")
QUESTION = "What is the monthly coworking limit for my team?"
CHUNK_TEXT = "Coworking reimbursement is limited to US$ 250 per month per employee."
ANSWER_TEXT = "The limit is US$ 250 per month [S1]."
PROVIDER_ECHO = "provider echoed: What is the monthly coworking limit"
LIMIT = make_retrieved_chunk(filename="expense-policy.pdf", page=2, text=CHUNK_TEXT)
# $1 / $2 per million tokens: 100 input + 20 output tokens cost 0.00014.
PRICES = PriceTable({"fake-chat-model": ModelPrice(input=1.0, output=2.0)})
ANSWERED = AnswerDraft(outcome="answered", answer=ANSWER_TEXT, closest_source_id=None)


def _use_case(
    chunks: Sequence[RetrievedChunk],
    *replies: Reply,
    rerank: bool = False,
    capture_content: bool = False,
    prices: PriceTable = PRICES,
    reports_usage: bool | Sequence[bool] = True,
) -> AnswerQuestion:
    return make_answering(
        FakeRetriever(chunks),
        FakeEmbeddings(8),
        FakeChatModel(*replies, reports_usage=reports_usage),
        rerank=rerank,
        prices=prices,
        capture_content=capture_content,
    )


def _by_name(spans: InMemorySpanExporter) -> dict[str, ReadableSpan]:
    finished = spans.get_finished_spans()
    named = {span.name: span for span in finished}
    assert len(named) == len(finished), "one span per step"
    return named


def _attrs(span: ReadableSpan) -> Mapping[str, AttributeValue]:
    return span.attributes or {}


def _is_child_of(span: ReadableSpan, root: ReadableSpan) -> bool:
    return (
        span.parent is not None
        and root.context is not None
        and span.parent.span_id == root.context.span_id
    )


def _exported_text(spans: InMemorySpanExporter) -> str:
    """Everything a backend would receive: names, attributes, events, status."""
    parts: list[str] = []
    for span in spans.get_finished_spans():
        parts.append(span.name)
        parts.extend(f"{key}={value!r}" for key, value in (span.attributes or {}).items())
        for event in span.events:
            parts.append(event.name)
            parts.extend(f"{key}={value!r}" for key, value in (event.attributes or {}).items())
        parts.append(span.status.description or "")
    return "\n".join(parts)


async def test_otel_chat_trace_success(spans: InMemorySpanExporter) -> None:
    use_case = _use_case([LIMIT], ANSWERED)

    await use_case.answer(OWNER, QUESTION, REQUEST_ID)

    named = _by_name(spans)
    root = named[t.CHAT]
    assert set(named) == {t.CHAT, t.RETRIEVAL_EMBED_QUERY, t.RETRIEVAL_HYBRID, t.ANSWER_GENERATION}
    assert root.parent is None
    for name in (t.RETRIEVAL_EMBED_QUERY, t.RETRIEVAL_HYBRID, t.ANSWER_GENERATION):
        assert _is_child_of(named[name], root)
    assert root.attributes is not None
    assert root.attributes[t.REQUEST_ID] == str(REQUEST_ID)
    assert root.attributes[t.OUTCOME] == "answered"
    assert root.attributes[t.GEN_AI_PROVIDER] == "fake"
    assert root.attributes[t.GEN_AI_REQUEST_MODEL] == "fake-chat-model"
    assert root.attributes[t.SOURCES] == 1
    assert root.attributes[t.GEN_AI_INPUT_TOKENS] == 100
    assert root.attributes[t.GEN_AI_OUTPUT_TOKENS] == 20
    assert root.attributes[t.COST_USD] == 0.00014
    # Per-step counts live on their own spans (retrieved vs used chunks).
    assert _attrs(named[t.RETRIEVAL_HYBRID])[t.RETRIEVAL_EVIDENCE] == 1
    assert _attrs(named[t.ANSWER_GENERATION])[t.CONTEXT_CHUNKS] == 1
    generation = named[t.ANSWER_GENERATION].attributes
    assert generation is not None
    assert generation[t.GEN_AI_RESPONSE_MODEL] == "fake-chat-model-2026"
    assert generation[t.GEN_AI_INPUT_TOKENS] == 100
    assert root.status.status_code is StatusCode.UNSET


async def test_otel_chat_trace_refusal_without_evidence(spans: InMemorySpanExporter) -> None:
    use_case = _use_case([])  # nothing retrieved: the chat model is never called

    await use_case.answer(OWNER, QUESTION)

    named = _by_name(spans)
    assert t.ANSWER_GENERATION not in named
    root = named[t.CHAT].attributes
    assert root is not None
    assert root[t.OUTCOME] == "refused"
    # No call reported usage: no totals and no cost, never a recorded 0 (DOM-24).
    assert not {t.GEN_AI_INPUT_TOKENS, t.GEN_AI_OUTPUT_TOKENS, t.COST_USD} & set(root)


async def test_otel_no_content_by_default(spans: InMemorySpanExporter) -> None:
    use_case = _use_case([LIMIT], ANSWERED)

    answer = await use_case.answer(OWNER, QUESTION)

    exported = _exported_text(spans)
    for content in (QUESTION, CHUNK_TEXT, ANSWER_TEXT, answer.text):
        assert content not in exported
    assert all(not span.events for span in spans.get_finished_spans())


async def test_otel_content_capture_uses_events_only(spans: InMemorySpanExporter) -> None:
    use_case = _use_case([LIMIT], ANSWERED, capture_content=True)

    await use_case.answer(OWNER, QUESTION)

    named = _by_name(spans)
    root_events = {e.name: e.attributes for e in named[t.CHAT].events}
    assert root_events[t.EVENT_QUESTION] == {t.CONTENT: QUESTION}
    prompt_events = {e.name: e.attributes for e in named[t.ANSWER_GENERATION].events}
    assert CHUNK_TEXT in str(prompt_events[t.EVENT_PROMPT])
    for span in named.values():  # DOM-22: never as attributes, even with capture on
        values = " ".join(str(v) for v in (span.attributes or {}).values())
        assert QUESTION not in values
        assert CHUNK_TEXT not in values


async def test_otel_provider_error_recorded(spans: InMemorySpanExporter) -> None:
    failure = ChatModelUnavailable()
    failure.__cause__ = RuntimeError(PROVIDER_ECHO)  # as the adapter chains it
    use_case = _use_case([LIMIT], failure)

    with pytest.raises(ChatModelUnavailable):
        await use_case.answer(OWNER, QUESTION)

    named = _by_name(spans)
    for name in (t.ANSWER_GENERATION, t.CHAT):
        span = named[name]
        assert span.status.status_code is StatusCode.ERROR
        assert span.attributes is not None
        assert span.attributes[t.ERROR_TYPE] == "ChatModelUnavailable"
        assert not span.events  # no exception event: message and stack trace stay out
    assert _attrs(named[t.CHAT])[t.OUTCOME] == "error"
    exported = _exported_text(spans)
    assert PROVIDER_ECHO not in exported
    assert QUESTION not in exported


async def test_otel_rerank_failure_marks_its_span_and_fails_open(
    spans: InMemorySpanExporter,
) -> None:
    use_case = _use_case([LIMIT], ChatModelUnavailable(), ANSWERED, rerank=True)

    await use_case.answer(OWNER, QUESTION)

    named = _by_name(spans)
    assert named[t.RERANK].status.status_code is StatusCode.ERROR
    root = named[t.CHAT]
    assert root.status.status_code is StatusCode.UNSET
    assert root.attributes is not None
    assert root.attributes[t.RERANKED] is False
    assert root.attributes[t.OUTCOME] == "answered"


async def test_otel_rerank_tokens_count_in_the_request_total(
    spans: InMemorySpanExporter,
) -> None:
    use_case = _use_case([LIMIT], RerankDraft(source_ids=["S1"]), ANSWERED, rerank=True)

    await use_case.answer(OWNER, QUESTION)

    named = _by_name(spans)
    assert _attrs(named[t.RERANK])[t.RERANK_KEPT] == 1
    root = named[t.CHAT].attributes
    assert root is not None
    assert root[t.GEN_AI_INPUT_TOKENS] == 200  # rerank + answer_generation
    assert root[t.COST_USD] == 0.00028


async def test_otel_unpriced_model_records_no_cost(spans: InMemorySpanExporter) -> None:
    use_case = _use_case([LIMIT], ANSWERED, prices=PriceTable())

    answer = await use_case.answer(OWNER, QUESTION)

    root = _by_name(spans)[t.CHAT].attributes
    assert root is not None
    assert t.COST_USD not in root  # DOM-24: unknown, never a wrong number
    assert root[t.GEN_AI_INPUT_TOKENS] == 100
    assert answer.usage == (FakeChatModel.USAGE_PER_CALL,)


async def test_otel_no_usage_no_cost(spans: InMemorySpanExporter) -> None:
    """CWYD-27 (DOM-24): a provider that returns no usage metadata records no tokens and no
    cost on the step or the question, never 0."""
    use_case = _use_case([LIMIT], ANSWERED, reports_usage=False)

    answer = await use_case.answer(OWNER, QUESTION)

    assert answer.outcome.value == "answered"
    for span in spans.get_finished_spans():
        recorded = set(_attrs(span))
        assert not any(key.startswith("gen_ai.usage.") for key in recorded), span.name
        assert t.COST_USD not in recorded, span.name


async def test_otel_call_without_usage_is_left_out_of_the_totals(
    spans: InMemorySpanExporter,
) -> None:
    """CWYD-27 (DOM-24): only calls that reported usage count toward the question's totals."""
    use_case = make_answering(
        FakeRetriever([LIMIT]),
        FakeEmbeddings(8),
        # The rerank call reports no usage; the answer call does.
        FakeChatModel(RerankDraft(source_ids=["S1"]), ANSWERED, reports_usage=[False, True]),
        rerank=True,
        prices=PRICES,
    )

    await use_case.answer(OWNER, QUESTION)

    named = _by_name(spans)
    assert t.GEN_AI_INPUT_TOKENS not in _attrs(named[t.RERANK])
    root = _attrs(named[t.CHAT])
    assert root[t.GEN_AI_INPUT_TOKENS] == 100  # the answer call only
    assert root[t.COST_USD] == 0.00014


async def test_otel_ingest_trace_success(spans: InMemorySpanExporter) -> None:
    service = make_ingestion(InMemoryDocumentRepository(), FakeEmbeddings(8))
    content = fixture_bytes("expense-policy.pdf")
    uploaded = await service.upload(OWNER, "expense-policy.pdf", content)

    await service.index(uploaded.document, content)

    named = _by_name(spans)
    root = named[t.INGEST]
    assert set(named) == {t.INGEST, t.INGEST_PARSE, t.INGEST_CHUNK, t.INGEST_EMBED, t.INGEST_STORE}
    for name in (t.INGEST_PARSE, t.INGEST_CHUNK, t.INGEST_EMBED, t.INGEST_STORE):
        assert _is_child_of(named[name], root)
    assert root.attributes is not None
    assert root.attributes[t.DOCUMENT_ID] == str(uploaded.document.id)
    assert root.attributes[t.DOCUMENT_STATUS] == DocumentStatus.READY.value
    chunks = named[t.INGEST_CHUNK].attributes
    assert chunks is not None
    chunk_count = chunks[t.DOCUMENT_CHUNKS]
    assert isinstance(chunk_count, int)
    assert chunk_count > 0


async def test_otel_ingest_provider_failure_recorded(spans: InMemorySpanExporter) -> None:
    service = make_ingestion(InMemoryDocumentRepository(), FailingEmbeddings())
    content = fixture_bytes("expense-policy.pdf")
    uploaded = await service.upload(OWNER, "expense-policy.pdf", content)

    await service.index(uploaded.document, content)

    named = _by_name(spans)
    assert t.INGEST_STORE not in named
    assert named[t.INGEST_EMBED].status.status_code is StatusCode.ERROR
    root = named[t.INGEST]
    assert root.status.status_code is StatusCode.ERROR
    assert root.attributes is not None
    assert root.attributes[t.ERROR_TYPE] == "EmbeddingUnavailable"
    assert root.attributes[t.DOCUMENT_STATUS] == DocumentStatus.FAILED.value
    assert root.attributes[t.DOCUMENT_FAILURE_REASON] == FailureReason.INDEXING_FAILED.value
