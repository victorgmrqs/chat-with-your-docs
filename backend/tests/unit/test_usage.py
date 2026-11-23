"""Price table and estimated cost (DOM-24)."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.adapters.price_table import load_price_table
from app.config import Settings
from app.domain.usage import ModelPrice, PriceTable, TokenUsage

TABLE = PriceTable(
    {
        "model-a": ModelPrice(input=1.0, output=2.0),
        "model-a-mini": ModelPrice(input=0.1, output=0.2),
    }
)


def test_price_table_matches_longest_prefix_of_reported_model() -> None:
    assert TABLE.price_for("model-a-mini-2026-01-01") == ModelPrice(input=0.1, output=0.2)
    assert TABLE.price_for("model-a-2026") == ModelPrice(input=1.0, output=2.0)
    assert TABLE.price_for("other") is None


def test_price_table_cost_sums_every_call() -> None:
    usage = [TokenUsage("model-a", 1_000, 500), TokenUsage("model-a-mini", 10_000, 0)]

    assert TABLE.cost(usage) == pytest.approx((1_000 * 1.0 + 500 * 2.0 + 10_000 * 0.1) / 1e6)


def test_price_table_cost_unknown_when_any_model_has_no_price() -> None:
    usage = [TokenUsage("model-a", 1_000, 500), TokenUsage("other", 1, 1)]

    assert TABLE.cost(usage) is None


def test_price_table_cost_zero_without_model_calls() -> None:
    assert TABLE.cost([]) == 0.0


def test_load_price_table_reads_yaml(tmp_path: Path) -> None:
    path = tmp_path / "prices.yaml"
    path.write_text("prices_usd_per_million_tokens:\n  model-a: {input: 1, output: 2}\n")

    assert load_price_table(path).price_for("model-a-x") == ModelPrice(input=1.0, output=2.0)


def test_load_price_table_rejects_negative_price(tmp_path: Path) -> None:
    path = tmp_path / "prices.yaml"
    path.write_text("prices_usd_per_million_tokens:\n  model-a: {input: -1, output: 2}\n")

    with pytest.raises(ValidationError):
        load_price_table(path)


def test_load_price_table_missing_file_fails(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_price_table(tmp_path / "missing.yaml")


def test_committed_price_table_is_valid() -> None:
    default_path = Settings.model_fields["price_table_path"].default

    assert load_price_table(default_path).prices
