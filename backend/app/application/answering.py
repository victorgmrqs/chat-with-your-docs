"""Question answering use case: retrieve, gate, rerank, generate, resolve citations."""

import logging
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field

from opentelemetry.trace import Span
from opentelemetry.util.types import AttributeValue

from app.application import telemetry as t
from app.application.ports import (
    ChatModelPort,
    EmbeddingPort,
    EmbeddingUnavailable,
    RerankerPort,
    RetrieverPort,
)
from app.application.prompts import AnswerDraft, answer_prompt, label_chunks
from app.domain.answers import (
    INSUFFICIENT_EVIDENCE_MESSAGE,
    Answer,
    ChatModelTimeout,
    ChatModelUnavailable,
    EmptyQuestion,
    NoReadyDocuments,
    Outcome,
    Passage,
    QuestionTooLong,
    RetrievalUnavailable,
    RetrievedChunk,
    Source,
    clean_question,
    resolve_citations,
)
from app.domain.usage import PriceTable, TokenUsage

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AnsweringLimits:
    question_max_chars: int
    retrieval_candidates: int
    retrieval_top_k: int
    min_relevance: float
    rerank_top_n: int
    context_token_budget: int


# Trace outcome per answer outcome (DOM-10: insufficient evidence is a refusal, not an error);
# `error` when the question raised (DOM-24).
_TRACE_OUTCOME = {Outcome.ANSWERED: "answered", Outcome.INSUFFICIENT_EVIDENCE: "refused"}


@dataclass(slots=True)
class _Run:
    """Content-free diagnostics for the log line and the trace of a question (DOM-12/13/22)."""

    request_id: uuid.UUID
    started: float
    candidates: int = 0
    evidence: int = 0
    context_chunks: int = 0
    invalid_citations: int = 0
    reranked: bool = False
    usage: list[TokenUsage] = field(default_factory=list)  # DOM-24: every chat model call


class AnswerQuestion:
    def __init__(
        self,
        retriever: RetrieverPort,
        embeddings: EmbeddingPort,
        chat: ChatModelPort,
        limits: AnsweringLimits,
        reranker: RerankerPort | None = None,
        *,
        prices: PriceTable | None = None,
        capture_content: bool = False,
    ) -> None:
        self._retriever = retriever
        self._embeddings = embeddings
        self._chat = chat
        self._limits = limits
        self._reranker = reranker  # None: RERANK_ENABLED=false
        self._prices = prices or PriceTable()  # empty: no cost recorded (DOM-24)
        self._capture_content = capture_content  # DOM-22: CAPTURE_CONTENT, dev only

    async def answer(
        self, owner_id: uuid.UUID, question: str, request_id: uuid.UUID | None = None
    ) -> Answer:
        """`request_id` comes from the API (DOM-23); a new one is made when called directly."""
        question = clean_question(question)
        if not question:
            raise EmptyQuestion
        if len(question) > self._limits.question_max_chars:
            raise QuestionTooLong(self._limits.question_max_chars)
        # DOM-07: owner and Ready status are set here, never by the client or the LLM.
        if not await self._retriever.has_ready_documents(owner_id):
            raise NoReadyDocuments

        run = _Run(request_id=request_id or uuid.uuid4(), started=time.perf_counter())
        with t.step(
            t.CHAT,
            {
                t.REQUEST_ID: str(run.request_id),  # DOM-23
                t.GEN_AI_PROVIDER: self._chat.provider,  # DOM-13
                t.GEN_AI_REQUEST_MODEL: self._chat.model,
                t.QUESTION_CHARS: len(question),
                t.RERANK_ENABLED: self._reranker is not None,
            },
        ) as span:
            t.add_content(span, t.EVENT_QUESTION, question, enabled=self._capture_content)
            try:
                answer = await self._answer(owner_id, question, run)
            except Exception as exc:  # any failure still gets its log line and trace summary
                self._finish(span, run, "error", "error", error_type=type(exc).__name__)
                raise
            self._finish(span, run, answer.outcome.value, _TRACE_OUTCOME[answer.outcome])
            span.set_attribute(t.SOURCES, len(answer.sources))
            t.add_content(span, t.EVENT_ANSWER, answer.text, enabled=self._capture_content)
        return answer

    async def _answer(self, owner_id: uuid.UUID, question: str, run: _Run) -> Answer:
        with t.step(t.RETRIEVAL_EMBED_QUERY, {t.EMBEDDED_TEXTS: 1}):
            try:
                [query_embedding] = await self._embeddings.embed_documents([question])
            except EmbeddingUnavailable:
                raise RetrievalUnavailable from None
        with t.step(
            t.RETRIEVAL_HYBRID,
            {
                t.RETRIEVAL_CANDIDATES_PER_BRANCH: self._limits.retrieval_candidates,
                t.RETRIEVAL_LIMIT: self._limits.retrieval_top_k,
            },
        ) as span:
            candidates = await self._retriever.search(
                owner_id,
                question,
                query_embedding,
                candidates=self._limits.retrieval_candidates,
                limit=self._limits.retrieval_top_k,
            )
            evidence = [
                c for c in candidates if c.is_evidence(self._limits.min_relevance)
            ]  # DOM-08
            run.candidates, run.evidence = len(candidates), len(evidence)
            span.set_attributes(
                {
                    t.RETRIEVAL_RETURNED: len(candidates),
                    t.RETRIEVAL_FTS_MATCHED: sum(c.fts_matched for c in candidates),
                    t.RETRIEVAL_EVIDENCE: len(evidence),
                }
            )
            if candidates:
                span.set_attribute(
                    t.RETRIEVAL_TOP_SIMILARITY, round(max(c.similarity for c in candidates), 4)
                )
        if not evidence:
            return self._insufficient(run, related=None)  # the chat model is not called

        evidence = await self._rerank(question, evidence, run)

        sources = label_chunks(evidence, self._limits.context_token_budget)  # DOM-11
        run.context_chunks = len(sources)
        prompt = answer_prompt(question, sources)
        with t.step(
            t.ANSWER_GENERATION, {**self._model_attributes(), t.CONTEXT_CHUNKS: len(sources)}
        ) as span:
            if self._capture_content:  # DOM-22; the joined prompt is only built when captured
                t.add_content(
                    span, t.EVENT_PROMPT, f"{prompt.system}\n\n{prompt.user}", enabled=True
                )
            generation = await self._chat.generate(prompt, AnswerDraft)
            draft = generation.value
            _record_usage(span, run, generation.usage)
            span.set_attribute(t.DRAFT_OUTCOME, draft.outcome)
            t.add_content(span, t.EVENT_DRAFT, draft.answer, enabled=self._capture_content)

        if draft.outcome == Outcome.ANSWERED.value:
            resolved = resolve_citations(draft.answer, sources)  # DOM-09
            run.invalid_citations = resolved.invalid_labels
            if resolved.sources:
                return self._build(run, Outcome.ANSWERED, resolved.text, resolved.sources, None)
        closest = sources.get((draft.closest_source_id or "").strip())
        return self._insufficient(run, related=closest)

    async def _rerank(
        self, question: str, evidence: list[RetrievedChunk], run: _Run
    ) -> list[RetrievedChunk]:
        if self._reranker is None:
            return evidence
        try:
            with t.step(
                t.RERANK, {**self._model_attributes(), t.RERANK_INPUT: len(evidence)}
            ) as span:
                generation = await self._reranker.rerank(
                    question, evidence, self._limits.rerank_top_n
                )
                _record_usage(span, run, generation.usage)
                reranked = generation.value
                span.set_attribute(t.RERANK_KEPT, len(reranked))
                if not reranked:
                    span.set_attribute(t.RERANK_FALLBACK, "no_valid_source")
        except (ChatModelTimeout, ChatModelUnavailable) as exc:
            # DOM-11: fail open, the fused order is still evidence-backed. The rerank span
            # already carries the error; the question goes on.
            logger.warning(
                "Reranker failed, using fused order: %s",
                type(exc).__name__,
                extra={"request_id": str(run.request_id), "error_type": type(exc).__name__},
            )
            return evidence
        if not reranked:  # DOM-11: no valid source id is a reranker failure, not missing evidence
            logger.warning(
                "Reranker kept no valid source, using fused order",
                extra={"request_id": str(run.request_id), "error_type": "EmptyRerank"},
            )
            return evidence
        run.reranked = True
        return reranked

    def _model_attributes(self) -> dict[str, AttributeValue]:
        return {
            t.GEN_AI_OPERATION: "chat",
            t.GEN_AI_PROVIDER: self._chat.provider,
            t.GEN_AI_REQUEST_MODEL: self._chat.model,
        }

    def _finish(
        self,
        span: Span,
        run: _Run,
        log_outcome: str,
        trace_outcome: str,
        error_type: str | None = None,
    ) -> None:
        """The question's log line and root span summary (DOM-12/13/22/24). Per-step counts
        stay on their own spans; the root carries the outcome, tokens and estimated cost."""
        self._log(run, outcome=log_outcome, error_type=error_type)
        span.set_attributes(
            {
                t.OUTCOME: trace_outcome,
                t.INVALID_CITATIONS: run.invalid_citations,
                t.RERANKED: run.reranked,
            }
        )
        if not run.usage:  # DOM-24: no call reported usage, so no totals and no cost, never 0
            return
        span.set_attributes(
            {
                t.GEN_AI_INPUT_TOKENS: sum(u.input_tokens for u in run.usage),
                t.GEN_AI_OUTPUT_TOKENS: sum(u.output_tokens for u in run.usage),
            }
        )
        cost = self._prices.cost(run.usage)
        if cost is not None:  # DOM-24: a model without a price records no cost
            span.set_attribute(t.COST_USD, round(cost, 8))

    def _insufficient(self, run: _Run, related: RetrievedChunk | None) -> Answer:
        # DOM-10: fixed message; the related passage carries no citation number.
        passage = Passage.from_chunk(related) if related is not None else None
        return self._build(
            run, Outcome.INSUFFICIENT_EVIDENCE, INSUFFICIENT_EVIDENCE_MESSAGE, [], passage
        )

    def _build(
        self,
        run: _Run,
        outcome: Outcome,
        text: str,
        sources: list[Source],
        related: Passage | None,
    ) -> Answer:
        return Answer(
            request_id=run.request_id,
            outcome=outcome,
            text=text,
            sources=sources,
            related_passage=related,
            provider=self._chat.provider,  # DOM-13
            model=self._chat.model,
            reranked=run.reranked,
            usage=tuple(run.usage),
        )

    def _log(self, run: _Run, *, outcome: str, error_type: str | None = None) -> None:
        """DOM-12/13: counts, timings, provider and model only; never question or answer text."""
        logger.info(
            "Question %s: %s",
            run.request_id,
            outcome,
            extra={
                "request_id": str(run.request_id),
                "outcome": outcome,
                "error_type": error_type,
                "provider": self._chat.provider,
                "model": self._chat.model,
                "candidates": run.candidates,
                "evidence": run.evidence,
                "context_chunks": run.context_chunks,
                "invalid_citations": run.invalid_citations,
                "reranked": run.reranked,
                "duration_ms": round((time.perf_counter() - run.started) * 1000),
            },
        )


def _record_usage(span: Span, run: _Run, usage: Sequence[TokenUsage]) -> None:
    """DOM-24: on the model call's span and in the question's total."""
    run.usage.extend(usage)
    t.record_usage(span, usage)
