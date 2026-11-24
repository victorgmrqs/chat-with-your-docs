"""Runs the golden dataset through the real pipeline for one configuration (DOM-20, DOM-21),
and the adversarial set, when given, as a separate collection (DOM-29).

Documents are indexed by the real IngestionService under an evaluation owner derived from the
settings that shape the stored chunks (and the collection), so evaluation data never mixes with
the UI owner's or the other collection's, and a re-run reuses what is already indexed
(DOM-04). Questions run one at a time: latency is per question and the retriever recording
belongs to the question being asked.
"""

import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.callbacks import get_usage_metadata_callback

from app.adapters.langchain_chat import token_usage
from app.application.answering import AnswerQuestion
from app.application.ingestion import IngestionService
from app.application.ports import ChatModelPort, EmbeddingPort, RetrieverPort
from app.composition import Container, build_container
from app.config import Settings
from app.domain.documents import DomainError
from app.domain.usage import PriceTable
from eval.dataset import Dataset, EvalConfig, GoldenQuestion
from eval.recording import Recorders, RecordingEmbeddings, RecordingRetriever
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
class AdversarialRun:
    """DOM-29: the prompt-injection cases, scored and summarized apart from the golden set."""

    dataset_sha256: str
    documents: list[DocumentRow]
    scores: list[QuestionScore]
    summary: Summary


@dataclass(frozen=True, slots=True)
class RunResult:
    config: EvalConfig
    settings: dict[str, Any]
    dataset_sha256: str
    started_at: datetime
    documents: list[DocumentRow]
    scores: list[QuestionScore]
    summary: Summary
    adversarial: AdversarialRun | None = None

    @property
    def partial_collection(self) -> bool:
        """Some document is not Ready: the questions ran on part of a collection."""
        documents = [*self.documents, *(self.adversarial.documents if self.adversarial else [])]
        return any(document.status != "ready" for document in documents)


def configured_settings(base: Settings, config: EvalConfig) -> Settings:
    """Environment settings, RAG knobs reset to their code defaults, then the overrides."""
    unknown = sorted(set(config.settings) - set(TUNED_SETTINGS))
    if unknown:
        raise ValueError(f"{config.name}: only RAG settings can be overridden, not {unknown}")
    defaults = {name: Settings.model_fields[name].default for name in TUNED_SETTINGS}
    return Settings.model_validate({**base.model_dump(), **defaults, **config.settings})


def eval_owner(settings: Settings, collection: str = "") -> uuid.UUID:
    """Same chunking, embedding model and collection, same owner: the indexed one is reused.

    The golden collection has no suffix, so its owner (and indexed data) predates CWYD-21.
    """
    key = f"{settings.embedding_model}:{settings.chunk_size}:{settings.chunk_overlap}"
    return uuid.uuid5(_OWNER_NAMESPACE, f"{key}:{collection}" if collection else key)


def build_eval_container(
    settings: Settings,
    embeddings: EmbeddingPort | None = None,
    chat: ChatModelPort | None = None,
) -> tuple[Container, Recorders]:
    """The application's own wiring, with the retriever and the embeddings recorded."""
    retrieval: RecordingRetriever | None = None
    embedding: RecordingEmbeddings | None = None

    def record_retrieval(inner: RetrieverPort) -> RetrieverPort:
        nonlocal retrieval
        retrieval = RecordingRetriever(inner)
        return retrieval

    def record_embeddings(inner: EmbeddingPort) -> EmbeddingPort:
        nonlocal embedding
        embedding = RecordingEmbeddings(inner)
        return embedding

    container = build_container(
        settings,
        embeddings,
        chat,
        wrap_retriever=record_retrieval,
        wrap_embeddings=record_embeddings,
    )
    if retrieval is None or embedding is None:  # build_container always builds both
        raise RuntimeError("build_container did not call wrap_retriever and wrap_embeddings")
    return container, Recorders(retrieval, embedding)


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
    recorder: Recorders,
    owner_id: uuid.UUID,
    question: GoldenQuestion,
    prices: PriceTable,
) -> Observation:
    """One question; a domain failure becomes the question's error (DOM-21), not a crash.

    Anything else is a bug in the evaluation or the pipeline and stops the run.
    """
    recorder.reset()
    started = time.perf_counter()
    # Context-wide, so a question that fails after a model call still counts its tokens.
    with get_usage_metadata_callback() as callback:
        try:
            answer = await answering.answer(owner_id, question.question)
            error = None
        except DomainError as exc:  # provider, retrieval or input failure of this question
            answer, error = None, type(exc).__name__
    latency_ms = (time.perf_counter() - started) * 1000

    # DOM-24: chat calls from LangChain's callback, the query embedding from its recorder.
    usage = [*token_usage(callback), *recorder.embeddings.usage]
    return Observation(
        question_id=question.id,
        outcome=answer.outcome.value if answer else None,
        retrieved=[ChunkRef.of(chunk) for chunk in recorder.retrieval.last],
        cited=[ChunkRef.of(source.passage) for source in answer.sources] if answer else [],
        latency_ms=latency_ms,
        input_tokens=sum(u.input_tokens for u in usage),
        output_tokens=sum(u.output_tokens for u in usage),
        cost_usd=prices.cost(usage),  # DOM-24: None when a model has no price
        error=error,
        reranked=answer.reranked if answer else False,
        answer=answer.text if answer else "",
    )


async def _run_collection(
    container: Container,
    recorder: Recorders,
    dataset: Dataset,
    owner_id: uuid.UUID,
    documents_dir: Path,
) -> tuple[list[DocumentRow], list[QuestionScore]]:
    documents = await index_documents(
        container.ingestion, owner_id, documents_dir, dataset.documents
    )
    scores = []
    for question in dataset.questions:
        observation = await ask(container.answering, recorder, owner_id, question, container.prices)
        scores.append(score_question(question, observation))
    return documents, scores


async def evaluate(
    container: Container,
    recorder: Recorders,
    dataset: Dataset,
    config: EvalConfig,
    documents_dir: Path,
    adversarial: Dataset | None = None,
) -> RunResult:
    settings = container.settings
    started_at = datetime.now(UTC)
    documents, scores = await _run_collection(
        container, recorder, dataset, eval_owner(settings), documents_dir
    )
    adversarial_run = None
    if adversarial is not None:
        owner_id = eval_owner(settings, "adversarial")
        adv_documents, adv_scores = await _run_collection(
            container, recorder, adversarial, owner_id, documents_dir
        )
        adversarial_run = AdversarialRun(
            adversarial.sha256, adv_documents, adv_scores, summarize(adv_scores)
        )
    return RunResult(
        config=config,
        settings={name: getattr(settings, name) for name in REPORTED_SETTINGS},
        dataset_sha256=dataset.sha256,
        started_at=started_at,
        documents=documents,
        scores=scores,
        summary=summarize(scores),
        adversarial=adversarial_run,
    )
