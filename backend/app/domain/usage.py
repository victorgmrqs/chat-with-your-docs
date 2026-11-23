"""Token usage of chat model calls and its estimated cost (DOM-24)."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TokenUsage:
    model: str  # as the provider reported it (may carry a date suffix)
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True, slots=True)
class ModelPrice:
    input: float  # USD per million tokens
    output: float


@dataclass(frozen=True, slots=True)
class PriceTable:
    prices: Mapping[str, ModelPrice] = field(default_factory=dict)

    def price_for(self, model: str) -> ModelPrice | None:
        """Longest configured name that prefixes the reported model (providers add suffixes)."""
        names = [name for name in self.prices if model.startswith(name)]
        return self.prices[max(names, key=len)] if names else None

    def cost(self, usages: Iterable[TokenUsage]) -> float | None:
        """USD for all `usages`; None when any model has no price (never a wrong number)."""
        total = 0.0
        for usage in usages:
            price = self.price_for(usage.model)
            if price is None:
                return None
            total += (usage.input_tokens * price.input + usage.output_tokens * price.output) / 1e6
        return total
