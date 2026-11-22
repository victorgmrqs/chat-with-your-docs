"""Runs the golden dataset through the real pipeline for one configuration (DOM-20, DOM-21).

Documents are indexed by the real IngestionService under an evaluation owner derived from the
settings that shape the stored chunks, so evaluation data never mixes with the UI owner's and a
re-run reuses what is already indexed (DOM-04). Questions run one at a time: latency is per
question and the retriever recording belongs to the question being asked.
"""

import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.callbacks import get_usage_metadata_callback

from app.application.answering import AnswerQuestion
from app.application.ingestion import IngestionService
from app.application.ports import ChatModelPort, EmbeddingPort, RetrieverPort
from app.composition import Container, build_container
from app.config import Settings
from app.domain.documents import DomainError
from eval.dataset import Dataset, EvalConfig, EvalPlan, GoldenQuestion
from eval.recording import RecordingRetriever
from eval.scoring import ChunkRef, Observation, QuestionScore, Summary, score_question, summarize

_OWNER_NAMESPACE = uuid.UUID("6f1c7d2e-2a39-4c55-9a43-0c7e1f3b9d10")

# RAG settings a configuration starts from at their code defaults (app/config.py), whatever the
# environment says, so a run does not depend on the local .env. Providers, models and keys still
# come from the environment.
TUNED_SETTINGS = (
    "chunk_size",
    "chunk_overlap",
    "retrieval_candidates",
    "retrieval_top_k",
    "min_relevance",
    "rerank_enabled",
    "rerank_top_n",
    "context_token_budget",
    "answer_max_tokens",
    "chat_temperature",
)

# Settings recorded in every report: what a reader needs to reproduce or compare a run.
REPORTED_SETTINGS = ("chat_provider", "chat_model", "embedding_model", *TUNED_SETTINGS)


@dataclass(frozen=True, slots=True)
class DocumentRow:
    filename: str
    status: str
    chunk_count: int
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class RunResult:
    config: EvalConfig
    settings: dict[str, Any]
    dataset_sha256: str
    started_at: datetime
    documents: list[DocumentRow]
    scores: list[QuestionScore]
    summary: Summary

    @property
    def partial_collection(self) -> bool:
        """Some document is not Ready: the questions ran on part of the collection."""
        return any(document.status != "ready" for document in self.documents)


def configured_settings(base: Settings, config: EvalConfig) -> Settings:
    """Environment settings, RAG knobs reset to their code defaults, then the overrides."""
    unknown = sorted(set(config.settings) - set(TUNED_SETTINGS))
    if unknown:
        raise ValueError(f"{config.name}: only RAG settings can be overridden, not {unknown}")
    defaults = {name: Settings.model_fields[name].default for name in TUNED_SETTINGS}
    return Settings.model_validate({**base.model_dump(), **defaults, **config.settings})


def eval_owner(settings: Settings) -> uuid.UUID:
    """Same chunking and embedding model, same owner: the indexed collection is reused."""
    key = f"{settings.embedding_model}:{settings.chunk_size}:{settings.chunk_overlap}"
    return uuid.uuid5(_OWNER_NAMESPACE, key)


def build_eval_container(
    settings: Settings,
    embeddings: EmbeddingPort | None = None,
    chat: ChatModelPort | None = None,
) -> tuple[Container, RecordingRetriever]:
    """The application's own wiring, with the retriever recorded for scoring."""
    recorder: RecordingRetriever | None = None

    def record(inner: RetrieverPort) -> RetrieverPort:
        nonlocal recorder
        recorder = RecordingRetriever(inner)
        return recorder

    container = build_container(settings, embeddings, chat, wrap_retriever=record)
    if recorder is None:  # build_container always builds the retriever
        raise RuntimeError("build_container did not call wrap_retriever")
    return container, recorder


async def index_documents(
    ingestion: IngestionService, owner_id: uuid.UUID, documents_dir: Path, names: Sequence[str]
) -> list[DocumentRow]:
    rows = []
    for name in names:
        content = (documents_dir / name).read_bytes()
        upload = await ingestion.upload(owner_id, name, content)
        document = upload.document
        if upload.needs_indexing:
            await ingestion.index(document, content)  # ends Ready or Failed (DOM-02)
            document = await ingestion.get(owner_id, document.id)
        reason = document.failure_reason.value if document.failure_reason else None
        rows.append(DocumentRow(name, document.status.value, document.chunk_count, reason))
    return rows


async def ask(
    answering: AnswerQuestion,
    recorder: RecordingRetriever,
    owner_id: uuid.UUID,
    question: GoldenQuestion,
    plan: EvalPlan,
) -> Observation:
    """One question; a domain failure becomes the question's error (DOM-21), not a crash.

    Anything else is a bug in the evaluation or the pipeline and stops the run.
    """
    recorder.reset()
    started = time.perf_counter()
    with get_usage_metadata_callback() as usage:
        try:
            answer = await answering.answer(owner_id, question.question)
            error = None
        except DomainError as exc:  # provider, retrieval or input failure of this question
            answer, error = None, type(exc).__name__
    latency_ms = (time.perf_counter() - started) * 1000

    used = usage.usage_metadata
    prices = {model_name: plan.price_for(model_name) for model_name in used}
    cost = (
        None  # a model without a configured price: unknown, never a wrong number
        if any(price is None for price in prices.values())
        else sum(
            (u["input_tokens"] * p.input + u["output_tokens"] * p.output) / 1e6
            for model_name, u in used.items()
            if (p := prices[model_name]) is not None
        )
    )
    return Observation(
        question_id=question.id,
        outcome=answer.outcome.value if answer else None,
        retrieved=[ChunkRef.of(chunk) for chunk in recorder.last],
        cited=[ChunkRef.of(source.passage) for source in answer.sources] if answer else [],
        latency_ms=latency_ms,
        input_tokens=sum(u["input_tokens"] for u in used.values()),
        output_tokens=sum(u["output_tokens"] for u in used.values()),
        cost_usd=cost,
        error=error,
        reranked=answer.reranked if answer else False,
    )


async def evaluate(
    container: Container,
    recorder: RecordingRetriever,
    dataset: Dataset,
    plan: EvalPlan,
    config: EvalConfig,
    documents_dir: Path,
) -> RunResult:
    settings = container.settings
    started_at = datetime.now(UTC)
    owner_id = eval_owner(settings)
    documents = await index_documents(
        container.ingestion, owner_id, documents_dir, dataset.documents
    )
    scores = []
    for question in dataset.questions:
        observation = await ask(container.answering, recorder, owner_id, question, plan)
        scores.append(score_question(question, observation))
    return RunResult(
        config=config,
        settings={name: getattr(settings, name) for name in REPORTED_SETTINGS},
        dataset_sha256=dataset.sha256,
        started_at=started_at,
        documents=documents,
        scores=scores,
        summary=summarize(scores),
    )
