"""Loads the chat model price table (DOM-24) from YAML."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.domain.usage import ModelPrice, PriceTable


class _Price(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: float = Field(ge=0)  # USD per million tokens
    output: float = Field(ge=0)


class _PriceFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prices_usd_per_million_tokens: dict[str, _Price] = {}


def load_price_table(path: Path) -> PriceTable:
    """Raises OSError when the file is missing and ValidationError when it is malformed:
    a configured table that cannot be read is a startup error, not an unknown cost."""
    data = _PriceFile.model_validate(yaml.safe_load(path.read_text()) or {})
    return PriceTable(
        {
            name: ModelPrice(input=price.input, output=price.output)
            for name, price in data.prices_usd_per_million_tokens.items()
        }
    )
