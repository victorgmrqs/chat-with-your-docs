"""Per-question scores and aggregates for the RAG evaluation (DOM-20, DOM-21). Pure functions."""

import math
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.domain.answers import Passage, RetrievedChunk
from eval.dataset import ExpectedSource, GoldenQuestion


@dataclass(frozen=True, slots=True)
class ChunkRef:
    """What scoring needs from a retrieved or cited chunk."""

    chunk_id: uuid.UUID
    filename: str
    page: int | None
    heading: str | None
    text: str

    @classmethod
    def of(cls, chunk: RetrievedChunk | Passage) -> ChunkRef:
        return cls(chunk.chunk_id, chunk.filename, chunk.page, chunk.heading, chunk.text)

    def matches(self, expected: ExpectedSource) -> bool:
        return expected.matches(self.filename, self.page, self.heading, self.text)


@dataclass(frozen=True, slots=True)
class Observation:
    """What one question produced. `outcome` is None when the pipeline raised (`error`)."""

    question_id: str
    outcome: str | None
    retrieved: Sequence[ChunkRef]  # fused top-k returned by the retriever, rank order
    cited: Sequence[ChunkRef]  # numbered sources of the answer
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None  # None: no price configured for the model
    error: str | None = None
    reranked: bool = False  # DOM-11: the reranker's order reached the prompt


@dataclass(frozen=True, slots=True)
class QuestionScore:
    question_id: str
    category: str
    expected_outcome: str
    outcome: str | None
    outcome_correct: bool
    hit_at_k: float | None  # share of expected sources in the top-k; None for refusal questions
    reciprocal_rank: float | None  # mean 1/rank of each expected source (0 if missed)
    refusal_correct: bool | None  # None for answerable questions
    citation_valid: bool | None  # None when nothing was cited
    citation_recall: float | None  # share of expected sources cited; None for refusal questions
    cited: int
    retrieved: int
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float | None
    error: str | None
    reranked: bool


def _share(expected: Sequence[ExpectedSource], chunks: Sequence[ChunkRef]) -> float:
    found = sum(1 for source in expected if any(chunk.matches(source) for chunk in chunks))
    return found / len(expected)


def _reciprocal_rank(expected: Sequence[ExpectedSource], chunks: Sequence[ChunkRef]) -> float:
    """Rank-aware companion of hit@k: 1.0 only when every expected source is ranked first."""

    def rank(source: ExpectedSource) -> float:
        position = next((i for i, c in enumerate(chunks, start=1) if c.matches(source)), None)
        return 1 / position if position else 0.0

    return sum(rank(source) for source in expected) / len(expected)


def score_question(question: GoldenQuestion, observation: Observation) -> QuestionScore:
    expected = question.expected_sources
    answerable = question.expected_outcome == "answered"
    retrieved_ids = {chunk.chunk_id for chunk in observation.retrieved}
    # DOM-20: a citation is valid only if retrieved for this question and expected.
    citation_valid = (
        all(
            chunk.chunk_id in retrieved_ids and any(chunk.matches(s) for s in expected)
            for chunk in observation.cited
        )
        if observation.cited
        else None
    )
    # DOM-21: only a sourceless insufficient_evidence is a correct refusal; an error never is.
    refused = observation.outcome == "insufficient_evidence" and not observation.cited
    return QuestionScore(
        question_id=question.id,
        category=question.category,
        expected_outcome=question.expected_outcome,
        outcome=observation.outcome,
        outcome_correct=observation.outcome == question.expected_outcome,
        hit_at_k=_share(expected, observation.retrieved) if answerable else None,
        reciprocal_rank=_reciprocal_rank(expected, observation.retrieved) if answerable else None,
        refusal_correct=None if answerable else refused,
        citation_valid=citation_valid,
        citation_recall=_share(expected, observation.cited) if answerable else None,
        cited=len(observation.cited),
        retrieved=len(observation.retrieved),
        latency_ms=observation.latency_ms,
        input_tokens=observation.input_tokens,
        output_tokens=observation.output_tokens,
        cost_usd=observation.cost_usd,
        error=observation.error,
        reranked=observation.reranked,
    )


@dataclass(frozen=True, slots=True)
class Summary:
    questions: int
    errors: int
    outcome_accuracy: float
    mean_hit_at_k: float | None
    mean_reciprocal_rank: float | None
    refusal_rate: float | None  # correct refusals / questions that expect a refusal
    citation_validity: float | None  # answers whose citations are all valid / answers citing
    mean_citation_recall: float | None
    latency_p50_ms: float
    latency_p95_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float | None  # None if any question used a model without a configured price
    reranked: int  # questions whose prompt used the reranker's order


def _mean(values: Iterable[float | bool | None]) -> float | None:
    """Mean of the values that apply (None skipped; True/False count as 1/0)."""
    present = [float(value) for value in values if value is not None]
    return sum(present) / len(present) if present else None


def _percentile(values: Sequence[float], percent: float) -> float:
    """Nearest-rank percentile; 0 for an empty run."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(percent / 100 * len(ordered)))
    return ordered[rank - 1]


def summarize(scores: Sequence[QuestionScore]) -> Summary:
    latencies = [s.latency_ms for s in scores]
    costs = [s.cost_usd for s in scores]
    return Summary(
        questions=len(scores),
        errors=sum(1 for s in scores if s.error is not None),
        outcome_accuracy=_mean(s.outcome_correct for s in scores) or 0.0,
        mean_hit_at_k=_mean(s.hit_at_k for s in scores),
        mean_reciprocal_rank=_mean(s.reciprocal_rank for s in scores),
        refusal_rate=_mean(s.refusal_correct for s in scores),
        citation_validity=_mean(s.citation_valid for s in scores),
        mean_citation_recall=_mean(s.citation_recall for s in scores),
        latency_p50_ms=_percentile(latencies, 50),
        latency_p95_ms=_percentile(latencies, 95),
        input_tokens=sum(s.input_tokens for s in scores),
        output_tokens=sum(s.output_tokens for s in scores),
        cost_usd=None if any(c is None for c in costs) else sum(c for c in costs if c is not None),
        reranked=sum(1 for s in scores if s.reranked),
    )
