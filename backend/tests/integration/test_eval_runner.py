"""RAG evaluation runner end to end: real PostgreSQL, fixture documents, declared LLM fakes.

The chat model is an oracle fake that cites the prompt sources holding the golden question's
expected passages, so what is verified is the evaluation itself: indexing under the eval owner,
the recorded retrieval, scoring and a complete report even when a question fails.
"""

from html import escape
from pathlib import Path

import pytest
import pytest_asyncio
from pydantic import BaseModel
from testcontainers.community.postgres import PostgresContainer

from app.application.ports import ChatPrompt, Generation
from app.application.prompts import AnswerDraft
from app.domain.answers import ChatModelUnavailable
from eval.dataset import EvalConfig, EvalPlan, load_dataset
from eval.report import write_run
from eval.runner import RunResult, build_eval_container, evaluate
from tests.factories import BACKEND_DIR, EMBEDDING_DIMENSIONS, FIXTURES_DIR, make_settings
from tests.fakes import EMBEDDING_TOKENS_PER_TEXT, KeywordEmbeddings, prompt_sources

pytestmark = pytest.mark.integration

DATASET = load_dataset(BACKEND_DIR / "eval/dataset.yaml")
ADVERSARIAL = load_dataset(BACKEND_DIR / "eval/adversarial.yaml")
PLAN = EvalPlan(configurations=[EvalConfig(name="baseline", description="Defaults.")])
FAILING_QUESTION = "parental_leave_duration"


class OracleChat:
    """Cites the sources holding the expected passages; fails for one question on purpose."""

    provider = "fake"
    model = "fake-chat-model"

    async def generate[T: BaseModel](self, prompt: ChatPrompt, schema: type[T]) -> Generation[T]:
        questions = [*DATASET.questions, *ADVERSARIAL.questions]
        question = next(q for q in questions if escape(q.question) in prompt.user)
        if question.id == FAILING_QUESTION:
            raise ChatModelUnavailable
        sources = prompt_sources(prompt)
        labels = [
            label
            for expected in question.expected_sources
            for label, body in sources.items()
            if expected.passage_contains in body
        ]
        if not labels:
            draft = AnswerDraft(outcome="insufficient_evidence", answer="", closest_source_id=None)
        else:
            answer = " ".join(f"Claim [{label}]." for label in dict.fromkeys(labels))
            draft = AnswerDraft(outcome="answered", answer=answer, closest_source_id=None)
        assert isinstance(draft, schema)
        return Generation(draft)


@pytest_asyncio.fixture(scope="module")
async def result(postgres: PostgresContainer) -> RunResult:
    """One evaluation shared by the tests of this module (13 questions, fakes only)."""
    settings = make_settings(postgres.get_connection_url())
    container, recorder = build_eval_container(
        settings, KeywordEmbeddings(EMBEDDING_DIMENSIONS), OracleChat()
    )
    try:
        return await evaluate(
            container, recorder, DATASET, PLAN.configurations[0], FIXTURES_DIR, ADVERSARIAL
        )
    finally:
        await container.engine.dispose()


def test_rag_eval_report_generated(result: RunResult, tmp_path: Path) -> None:
    write_run(result, tmp_path)

    scores = {s.question_id: s for s in result.scores}
    assert list(scores) == [q.id for q in DATASET.questions]
    assert {d.status for d in result.documents} == {"ready"}
    assert scores[FAILING_QUESTION].error == "ChatModelUnavailable"
    assert result.summary.errors == 1
    report = (tmp_path / "baseline.md").read_text()
    assert all(f"`{q.id}`" in report for q in DATASET.questions)
    assert (tmp_path / "baseline.json").exists()


def test_rag_eval_adversarial_collection_scored_apart(result: RunResult) -> None:
    # DOM-29: own documents and owner; the oracle resists, so every case passes.
    adversarial = result.adversarial
    assert adversarial is not None
    assert [s.question_id for s in adversarial.scores] == [q.id for q in ADVERSARIAL.questions]
    assert {d.status for d in adversarial.documents} == {"ready"}
    assert adversarial.summary.injection_resistance == 1.0
    assert result.summary.injection_resistance is None


def test_rag_eval_two_source_question_end_to_end(result: RunResult) -> None:
    score = next(s for s in result.scores if s.question_id == "coworking_two_sources")
    assert score.outcome == "answered"
    assert score.hit_at_k == 1.0
    assert score.citation_valid is True
    assert score.citation_recall == 1.0


def test_rag_eval_counts_each_query_embedding(result: RunResult) -> None:
    """CWYD-28 (DOM-24): each question's tokens include its own query embedding, also when the
    chat call failed afterwards; indexing tokens are not charged to any question. The oracle
    chat reports no usage, so the query embedding is all there is."""
    assert {s.input_tokens for s in result.scores} == {EMBEDDING_TOKENS_PER_TEXT}
