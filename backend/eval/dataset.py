"""Golden dataset and evaluation configurations, validated on load (DOM-20)."""

import hashlib
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal["single_source", "two_sources", "exact_term", "not_covered", "unrelated"]
ExpectedOutcome = Literal["answered", "insufficient_evidence"]


def _normalize(text: str) -> str:
    """Whitespace-insensitive comparison: PDF extraction may break or join lines."""
    return " ".join(text.split()).casefold()


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExpectedSource(_Strict):
    filename: str
    page: int | None = Field(default=None, ge=1)  # PDF, 1-based
    heading_contains: str | None = None  # Markdown heading path
    passage_contains: str

    def matches(self, filename: str, page: int | None, heading: str | None, text: str) -> bool:
        """DOM-20: file, page or heading, and passage must all agree."""
        if filename != self.filename:
            return False
        if self.page is not None and page != self.page:
            return False
        if self.heading_contains is not None and (
            heading is None or _normalize(self.heading_contains) not in _normalize(heading)
        ):
            return False
        return _normalize(self.passage_contains) in _normalize(text)


class GoldenQuestion(_Strict):
    id: str
    category: Category
    question: str
    expected_outcome: ExpectedOutcome
    expected_sources: list[ExpectedSource] = []

    @model_validator(mode="after")
    def _sources_match_outcome(self) -> GoldenQuestion:
        if self.expected_outcome == "answered" and not self.expected_sources:
            raise ValueError(f"{self.id}: an answered question lists its expected sources")
        if self.expected_outcome == "insufficient_evidence" and self.expected_sources:
            raise ValueError(f"{self.id}: a refusal question has no expected sources")
        return self


class Dataset(_Strict):
    documents: list[str]
    questions: list[GoldenQuestion]
    sha256: str = ""  # of the file, recorded in every report for reproducibility

    @model_validator(mode="after")
    def _unique_ids(self) -> Dataset:
        ids = [q.id for q in self.questions]
        if len(ids) != len(set(ids)):
            raise ValueError("question ids must be unique")
        return self


class ModelPrice(_Strict):
    input: float = Field(ge=0)  # USD per million tokens
    output: float = Field(ge=0)


class EvalConfig(_Strict):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")  # also the report file name
    description: str
    settings: dict[str, Any] = {}  # overrides applied on top of the environment's Settings


class EvalPlan(_Strict):
    prices_usd_per_million_tokens: dict[str, ModelPrice] = {}
    configurations: list[EvalConfig]

    def price_for(self, model_name: str) -> ModelPrice | None:
        """Longest configured name that prefixes the reported model (providers add suffixes)."""
        names = [name for name in self.prices_usd_per_million_tokens if model_name.startswith(name)]
        return self.prices_usd_per_million_tokens[max(names, key=len)] if names else None


def load_dataset(path: Path) -> Dataset:
    raw = path.read_bytes()
    data = yaml.safe_load(raw)
    return Dataset.model_validate({**data, "sha256": hashlib.sha256(raw).hexdigest()})


def load_plan(path: Path) -> EvalPlan:
    return EvalPlan.model_validate(yaml.safe_load(path.read_bytes()))
