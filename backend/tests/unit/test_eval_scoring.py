"""RAG evaluation scoring (DOM-20, DOM-21) and report rendering: pure functions, no I/O."""

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from eval.dataset import (
    EvalConfig,
    EvalPlan,
    ExpectedSource,
    GoldenQuestion,
    load_dataset,
    load_plan,
)
from eval.report import render_comparison, render_run
from eval.run import _selected
from eval.runner import DocumentRow, RunResult, configured_settings
from eval.scoring import ChunkRef, Observation, score_question, summarize
from tests.factories import BACKEND_DIR, FIXTURES_DIR, make_settings

APPROVAL = ChunkRef(
    uuid.uuid4(),
    "remote-work-policy.pdf",
    2,
    None,
    "Working from a coworking space\nrequires prior manager approval.",
)
LIMIT = ChunkRef(
    uuid.uuid4(),
    "expense-policy.pdf",
    2,
    None,
    "Coworking reimbursement is limited to US$ 250 per month per employee.",
)
HANDBOOK = ChunkRef(uuid.uuid4(), "office-handbook.txt", None, None, "The office opens at 8 a.m.")
DURATION = ChunkRef(
    uuid.uuid4(),
    "parental-leave-policy.md",
    None,
    "Parental Leave Policy > Duration",
    "Eligible employees receive sixteen weeks of paid parental leave.",
)

TWO_SOURCES = GoldenQuestion(
    id="coworking_two_sources",
    category="two_sources",
    question="Can I work from a coworking space, and what is the monthly reimbursement limit?",
    expected_outcome="answered",
    expected_sources=[
        ExpectedSource(
            filename="remote-work-policy.pdf",
            page=2,
            passage_contains="requires prior manager approval",
        ),
        ExpectedSource(filename="expense-policy.pdf", page=2, passage_contains="US$ 250 per month"),
    ],
)
NOT_COVERED = GoldenQuestion(
    id="leave_split_not_covered",
    category="not_covered",
    question="Can parental leave be split into several separate periods?",
    expected_outcome="insufficient_evidence",
)


def _observation(**overrides: Any) -> Observation:
    values: dict[str, Any] = {
        "question_id": "q",
        "outcome": "answered",
        "retrieved": [],
        "cited": [],
        "latency_ms": 100.0,
    }
    return Observation(**{**values, **overrides})


def test_rag_eval_two_source_question() -> None:
    observation = _observation(retrieved=[HANDBOOK, APPROVAL, LIMIT], cited=[APPROVAL, LIMIT])

    score = score_question(TWO_SOURCES, observation)

    assert score.outcome_correct
    assert score.hit_at_k == 1.0
    assert score.citation_valid is True
    assert score.citation_recall == 1.0
    assert score.refusal_correct is None


def test_rag_eval_two_source_question_one_source_missed() -> None:
    observation = _observation(retrieved=[HANDBOOK, LIMIT], cited=[LIMIT])

    score = score_question(TWO_SOURCES, observation)

    assert score.hit_at_k == 0.5
    assert score.citation_recall == 0.5
    assert score.citation_valid is True


def test_rag_eval_citation_not_retrieved_is_invalid() -> None:
    # DOM-20: a citation must come from what retrieval returned for this question.
    observation = _observation(retrieved=[APPROVAL], cited=[APPROVAL, LIMIT])

    assert score_question(TWO_SOURCES, observation).citation_valid is False


def test_rag_eval_citation_of_unexpected_source_is_invalid() -> None:
    observation = _observation(retrieved=[APPROVAL, HANDBOOK], cited=[APPROVAL, HANDBOOK])

    assert score_question(TWO_SOURCES, observation).citation_valid is False


def test_rag_eval_out_of_scope_refusal() -> None:
    observation = _observation(outcome="insufficient_evidence", retrieved=[DURATION])

    score = score_question(NOT_COVERED, observation)

    assert score.outcome_correct
    assert score.refusal_correct is True
    assert score.citation_valid is None
    assert score.hit_at_k is None


def test_rag_eval_out_of_scope_sourced_answer_fails_refusal() -> None:
    # DOM-21: a sourced answer to an uncovered question is a failed refusal.
    observation = _observation(retrieved=[DURATION], cited=[DURATION])

    score = score_question(NOT_COVERED, observation)

    assert score.refusal_correct is False
    assert score.citation_valid is False


def test_rag_eval_error_is_not_a_refusal() -> None:
    # DOM-21: a technical failure never counts as a correct refusal.
    observation = _observation(outcome=None, error="ChatModelUnavailable")

    score = score_question(NOT_COVERED, observation)

    assert score.refusal_correct is False
    assert not score.outcome_correct
    assert score.error == "ChatModelUnavailable"


@pytest.mark.parametrize(
    ("source", "matches"),
    [
        (ExpectedSource(filename="a.md", heading_contains="Duration", passage_contains="x"), True),
        (ExpectedSource(filename="a.md", heading_contains="Contract", passage_contains="x"), False),
        (ExpectedSource(filename="a.md", page=1, passage_contains="x"), False),
        (ExpectedSource(filename="b.md", passage_contains="x"), False),
        (ExpectedSource(filename="a.md", passage_contains="sixteen  WEEKS"), True),
    ],
)
def test_expected_source_matches(source: ExpectedSource, matches: bool) -> None:
    text = "Eligible employees receive sixteen\nweeks of paid parental leave. x"

    assert source.matches("a.md", None, "Policy > Duration", text) is matches


def test_golden_question_answered_requires_sources() -> None:
    with pytest.raises(ValidationError, match="expected sources"):
        GoldenQuestion(id="q", category="single_source", question="?", expected_outcome="answered")


def test_summarize_aggregates() -> None:
    scores = [
        score_question(TWO_SOURCES, _observation(retrieved=[APPROVAL, LIMIT], cited=[APPROVAL])),
        score_question(NOT_COVERED, _observation(outcome="insufficient_evidence", latency_ms=300)),
        score_question(NOT_COVERED, _observation(outcome=None, error="ChatModelTimeout")),
    ]

    summary = summarize(scores)

    assert summary.questions == 3
    assert summary.errors == 1
    assert summary.mean_hit_at_k == 1.0
    assert summary.refusal_rate == 0.5
    assert summary.citation_validity == 1.0
    assert summary.mean_citation_recall == 0.5
    assert summary.latency_p50_ms == 100.0
    assert summary.latency_p95_ms == 300.0


def test_summarize_cost_unknown_when_a_model_has_no_price() -> None:
    scores = [
        score_question(NOT_COVERED, _observation(cost_usd=0.001)),
        score_question(NOT_COVERED, _observation(cost_usd=None)),
    ]

    assert summarize(scores).cost_usd is None


def test_committed_dataset_and_plan_are_valid() -> None:
    dataset = load_dataset(BACKEND_DIR / "eval/dataset.yaml")
    plan = load_plan(BACKEND_DIR / "eval/configs.yaml")

    assert {q.category for q in dataset.questions} == {
        "single_source",
        "two_sources",
        "exact_term",
        "not_covered",
        "unrelated",
    }
    assert all((FIXTURES_DIR / d).exists() for d in dataset.documents)
    assert len(plan.configurations) >= 2


def test_rag_eval_report_generated_with_failed_questions() -> None:
    scores = [
        score_question(TWO_SOURCES, _observation(retrieved=[APPROVAL, LIMIT], cited=[APPROVAL])),
        score_question(NOT_COVERED, _observation(outcome=None, error="ChatModelUnavailable")),
    ]
    result = RunResult(
        config=EvalConfig(name="baseline", description="Defaults."),
        settings={"rerank_enabled": False},
        dataset_sha256="0" * 64,
        started_at=datetime(2026, 11, 22, tzinfo=UTC),
        documents=[],
        scores=scores,
        summary=summarize(scores),
    )

    report = render_run(result)
    comparison = render_comparison([result, result])

    assert "`coworking_two_sources`" in report
    assert "error: ChatModelUnavailable" in report
    assert "| Questions (errors) | 2 (1) |" in report
    assert comparison.count("| Correct refusal rate |") == 1


def test_price_matches_reported_model_by_prefix(tmp_path: Path) -> None:
    plan_file = tmp_path / "plan.yaml"
    plan_file.write_text(
        "prices_usd_per_million_tokens:\n"
        "  model-a: {input: 1, output: 2}\n"
        "  model-a-mini: {input: 0.1, output: 0.2}\n"
        "configurations: [{name: base, description: d}]\n"
    )
    plan = load_plan(plan_file)

    assert plan.price_for("model-a-mini-2026") == plan.prices_usd_per_million_tokens["model-a-mini"]
    assert plan.price_for("other") is None


def test_rag_eval_reciprocal_rank_rewards_top_ranks() -> None:
    observation = _observation(retrieved=[APPROVAL, HANDBOOK, LIMIT], cited=[APPROVAL, LIMIT])

    score = score_question(TWO_SOURCES, observation)

    assert score.reciprocal_rank == pytest.approx((1 / 1 + 1 / 3) / 2)


def test_configured_settings_start_from_code_defaults() -> None:
    # A local .env with RERANK_ENABLED=true must not leak into the baseline.
    base = make_settings("postgresql+asyncpg://u:p@db:5432/cwyd", rerank_enabled=True)
    config = EvalConfig(name="small", description="d", settings={"chunk_size": 300})

    settings = configured_settings(base, config)

    assert settings.rerank_enabled is False
    assert settings.chunk_size == 300
    assert settings.chat_model == base.chat_model


def test_configured_settings_reject_non_rag_overrides() -> None:
    config = EvalConfig(name="bad", description="d", settings={"chat_model": "other"})
    base = make_settings("postgresql+asyncpg://u:p@db:5432/cwyd")

    with pytest.raises(ValueError, match="only RAG settings"):
        configured_settings(base, config)


def test_eval_run_unknown_config_exits() -> None:
    plan = EvalPlan(configurations=[EvalConfig(name="baseline", description="d")])

    with pytest.raises(SystemExit, match="missing"):
        _selected(plan, ["baseline", "missing"])


def test_rag_eval_report_warns_on_partial_collection() -> None:
    scores = [score_question(NOT_COVERED, _observation(outcome="insufficient_evidence"))]
    result = RunResult(
        config=EvalConfig(name="baseline", description="Defaults."),
        settings={},
        dataset_sha256="0" * 64,
        started_at=datetime(2026, 11, 22, tzinfo=UTC),
        documents=[DocumentRow("expense-policy.pdf", "failed", 0, "indexing_failed")],
        scores=scores,
        summary=summarize(scores),
    )

    assert "partial collection" in render_run(result)
