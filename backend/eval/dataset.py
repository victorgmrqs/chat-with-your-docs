"""Golden and adversarial datasets and evaluation configurations, validated on load.

DOM-20/21 for the golden set, DOM-29 for the adversarial (prompt-injection) set.
"""

import hashlib
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal[
    "single_source", "two_sources", "exact_term", "not_covered", "unrelated", "adversarial"
]
Attack = Literal[
    "direct_override",
    "fake_system_tag",
    "reveal_system_prompt",
    "leak_other_document",
    "hidden_pdf_text",
    "fake_citation",
    "injected_evidence",
]
ExpectedOutcome = Literal["answered", "insufficient_evidence"]


def normalize(text: str) -> str:
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
            heading is None or normalize(self.heading_contains) not in normalize(heading)
        ):
            return False
        return normalize(self.passage_contains) in normalize(text)


class GoldenQuestion(_Strict):
    id: str
    category: Category
    question: str
    expected_outcome: ExpectedOutcome
    expected_sources: list[ExpectedSource] = []
    # DOM-29, adversarial questions only: the injection tried, and what the answer must avoid.
    attack: Attack | None = None
    forbidden_text: list[str] = []  # canaries the injection asks for, matched case-insensitively
    forbidden_files: list[str] = []  # documents that must never be cited

    @model_validator(mode="after")
    def _sources_match_outcome(self) -> GoldenQuestion:
        if self.expected_outcome == "answered" and not self.expected_sources:
            raise ValueError(f"{self.id}: an answered question lists its expected sources")
        if self.expected_outcome == "insufficient_evidence" and self.expected_sources:
            raise ValueError(f"{self.id}: a refusal question has no expected sources")
        return self

    @model_validator(mode="after")
    def _attack_only_when_adversarial(self) -> GoldenQuestion:
        adversarial = self.category == "adversarial"
        if adversarial != (self.attack is not None):
            raise ValueError(f"{self.id}: an attack is set exactly on adversarial questions")
        if not adversarial and (self.forbidden_text or self.forbidden_files):
            raise ValueError(f"{self.id}: forbidden text and files are for adversarial questions")
        return self

    @property
    def adversarial(self) -> bool:
        return self.attack is not None


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


class EvalConfig(_Strict):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")  # also the report file name
    description: str
    settings: dict[str, Any] = {}  # overrides applied on top of the environment's Settings


class EvalPlan(_Strict):
    configurations: list[EvalConfig]  # prices: app/prices.yaml, shared with the API (DOM-24)


def load_dataset(path: Path) -> Dataset:
    raw = path.read_bytes()
    data = yaml.safe_load(raw)
    return Dataset.model_validate({**data, "sha256": hashlib.sha256(raw).hexdigest()})


def load_plan(path: Path) -> EvalPlan:
    return EvalPlan.model_validate(yaml.safe_load(path.read_bytes()))
