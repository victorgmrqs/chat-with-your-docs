"""Span and attribute names (one place) and helpers over the OpenTelemetry API.

Only the vendor-neutral API is imported here: without an SDK configured (OTEL_TRACES_EXPORTER
=none) every call is a no-op. The SDK and exporters live in app/adapters/telemetry.py.

DOM-22: attributes carry counts, sizes, ids, model names and token usage only. Question,
prompt, chunk and answer text go to span events, and only when content capture is on.
"""

from collections.abc import Generator, Mapping, Sequence
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode
from opentelemetry.util.types import AttributeValue

from app.domain.usage import PriceTable, TokenUsage

tracer = trace.get_tracer("cwyd")

# Spans: one root per pipeline run, one child per real step.
CHAT = "rag.chat"
RETRIEVAL_EMBED_QUERY = "retrieval.embed_query"
RETRIEVAL_HYBRID = "retrieval.hybrid"  # vector + full-text + RRF run as one SQL statement
RERANK = "rerank"
ANSWER_GENERATION = "answer_generation"
INGEST = "ingest.document"
INGEST_PARSE = "ingest.parse"
INGEST_CHUNK = "ingest.chunk"
INGEST_EMBED = "ingest.embed"
INGEST_STORE = "ingest.store"

# OpenTelemetry semantic conventions (GenAI and error).
GEN_AI_OPERATION = "gen_ai.operation.name"
GEN_AI_PROVIDER = "gen_ai.provider.name"
GEN_AI_REQUEST_MODEL = "gen_ai.request.model"
GEN_AI_RESPONSE_MODEL = "gen_ai.response.model"
GEN_AI_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GEN_AI_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
ERROR_TYPE = "error.type"

# Application attributes.
REQUEST_ID = "app.request_id"
OUTCOME = "app.outcome"  # answered | refused | error
COST_USD = "app.cost.usd"  # absent when a model has no price (DOM-24)
QUESTION_CHARS = "app.question.chars"
RERANK_ENABLED = "app.rerank.enabled"
RERANKED = "app.reranked"
RERANK_INPUT = "app.rerank.input_chunks"
RERANK_KEPT = "app.rerank.kept_chunks"
RERANK_FALLBACK = "app.rerank.fallback"  # why the fused order was kept
RETRIEVAL_CANDIDATES_PER_BRANCH = "app.retrieval.candidates_per_branch"
RETRIEVAL_LIMIT = "app.retrieval.limit"
RETRIEVAL_RETURNED = "app.retrieval.returned"  # fused chunks returned
RETRIEVAL_FTS_MATCHED = "app.retrieval.fts_matched"  # of those, found by full-text too
RETRIEVAL_TOP_SIMILARITY = "app.retrieval.top_similarity"
RETRIEVAL_EVIDENCE = "app.retrieval.evidence"  # past the relevance gate (DOM-08)
CONTEXT_CHUNKS = "app.context.chunks"  # chunks that reached the prompt (DOM-11)
DRAFT_OUTCOME = "app.draft.outcome"  # what the model said, before citation checks
SOURCES = "app.answer.sources"  # cited chunks in the response
INVALID_CITATIONS = "app.answer.invalid_citations"  # dropped invented labels (DOM-09)
EMBEDDED_TEXTS = "app.embedding.texts"
DOCUMENT_ID = "app.document.id"
DOCUMENT_FORMAT = "app.document.format"
DOCUMENT_BYTES = "app.document.bytes"
DOCUMENT_STATUS = "app.document.status"
DOCUMENT_FAILURE_REASON = "app.document.failure_reason"
DOCUMENT_SECTIONS = "app.document.sections"
DOCUMENT_CHUNKS = "app.document.chunks"

# Content events (DOM-22: only with CAPTURE_CONTENT=true) and their single attribute.
EVENT_QUESTION = "app.content.question"
EVENT_PROMPT = "app.content.prompt"
EVENT_DRAFT = "app.content.draft"  # the model's structured answer, before citation checks
EVENT_ANSWER = "app.content.answer"
CONTENT = "app.content"


@contextmanager
def step(name: str, attributes: Mapping[str, AttributeValue] | None = None) -> Generator[Span]:
    """Current span for one pipeline step; an exception marks it failed and propagates.

    The SDK's own exception recording is off: a chained exception's message and stack trace
    can carry provider text that echoes the prompt (DOM-22).
    """
    with tracer.start_as_current_span(
        name, attributes=attributes, record_exception=False, set_status_on_exception=False
    ) as span:
        try:
            yield span
        except BaseException as exc:
            mark_failed(span, exc)
            raise


def current_span() -> Span:
    return trace.get_current_span()


def mark_failed(span: Span, exc: BaseException) -> None:
    """Error status and the exception type only (DOM-22)."""
    error_type = type(exc).__name__
    span.set_attribute(ERROR_TYPE, error_type)
    span.set_status(Status(StatusCode.ERROR, error_type))


def record_usage(span: Span, usage: Sequence[TokenUsage]) -> None:
    """Tokens of one step's model call(s) (DOM-24); nothing when the provider reported none."""
    if not usage:
        return
    span.set_attributes(
        {
            GEN_AI_RESPONSE_MODEL: usage[-1].model,
            GEN_AI_INPUT_TOKENS: sum(u.input_tokens for u in usage),
            GEN_AI_OUTPUT_TOKENS: sum(u.output_tokens for u in usage),
        }
    )


def record_cost(span: Span, prices: PriceTable, usage: Sequence[TokenUsage]) -> float | None:
    """Estimated USD cost of `usage` (DOM-24), also returned; nothing when no usage was
    reported or a model has no price: unknown, never 0 or a wrong number."""
    if not usage:
        return None
    cost = prices.cost(usage)
    if cost is None:
        return None
    cost = round(cost, 8)
    span.set_attribute(COST_USD, cost)
    return cost


def add_content(span: Span, event: str, text: str, *, enabled: bool) -> None:
    """DOM-22: text goes only to an event, and only when content capture is on."""
    if enabled:
        span.add_event(event, {CONTENT: text})
