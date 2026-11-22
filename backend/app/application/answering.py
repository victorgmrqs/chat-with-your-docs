"""Question answering use case: retrieve, gate, rerank, generate, resolve citations."""

import logging
import time
import uuid
from dataclasses import dataclass

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

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AnsweringLimits:
    question_max_chars: int
    retrieval_candidates: int
    retrieval_top_k: int
    min_relevance: float
    rerank_top_n: int
    context_token_budget: int


@dataclass(slots=True)
class _Run:
    """Content-free diagnostics for the single log line of a question (DOM-12/13)."""

    request_id: uuid.UUID
    started: float
    candidates: int = 0
    evidence: int = 0
    context_chunks: int = 0
    invalid_citations: int = 0
    reranked: bool = False


class AnswerQuestion:
    def __init__(
        self,
        retriever: RetrieverPort,
        embeddings: EmbeddingPort,
        chat: ChatModelPort,
        limits: AnsweringLimits,
        reranker: RerankerPort | None = None,
    ) -> None:
        self._retriever = retriever
        self._embeddings = embeddings
        self._chat = chat
        self._limits = limits
        self._reranker = reranker  # None: RERANK_ENABLED=false

    async def answer(self, owner_id: uuid.UUID, question: str) -> Answer:
        question = clean_question(question)
        if not question:
            raise EmptyQuestion
        if len(question) > self._limits.question_max_chars:
            raise QuestionTooLong(self._limits.question_max_chars)
        # DOM-07: owner and Ready status are set here, never by the client or the LLM.
        if not await self._retriever.has_ready_documents(owner_id):
            raise NoReadyDocuments

        run = _Run(request_id=uuid.uuid4(), started=time.perf_counter())
        try:
            answer = await self._answer(owner_id, question, run)
        except Exception as exc:  # any failure still gets its content-free log line
            self._log(run, outcome="error", error_type=type(exc).__name__)
            raise
        self._log(run, outcome=answer.outcome.value)
        return answer

    async def _answer(self, owner_id: uuid.UUID, question: str, run: _Run) -> Answer:
        try:
            [query_embedding] = await self._embeddings.embed_documents([question])
        except EmbeddingUnavailable:
            raise RetrievalUnavailable from None
        candidates = await self._retriever.search(
            owner_id,
            question,
            query_embedding,
            candidates=self._limits.retrieval_candidates,
            limit=self._limits.retrieval_top_k,
        )
        evidence = [c for c in candidates if c.is_evidence(self._limits.min_relevance)]  # DOM-08
        run.candidates, run.evidence = len(candidates), len(evidence)
        if not evidence:
            return self._insufficient(run, related=None)  # the chat model is not called

        evidence = await self._rerank(question, evidence, run)

        sources = label_chunks(evidence, self._limits.context_token_budget)  # DOM-11
        run.context_chunks = len(sources)
        draft = await self._chat.generate(answer_prompt(question, sources), AnswerDraft)

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
            reranked = await self._reranker.rerank(question, evidence, self._limits.rerank_top_n)
        except (ChatModelTimeout, ChatModelUnavailable) as exc:
            # DOM-11: fail open, the fused order is still evidence-backed.
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
