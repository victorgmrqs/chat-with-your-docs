"""LLM reranker over ChatModelPort (RERANK_ENABLED). Provider-neutral."""

from collections.abc import Sequence

from app.application.ports import ChatModelPort, Generation
from app.application.prompts import RerankDraft, rerank_prompt
from app.domain.answers import RetrievedChunk


class LLMReranker:
    """RerankerPort: asks the configured chat model to order the evidence chunks."""

    def __init__(self, chat: ChatModelPort) -> None:
        self._chat = chat

    async def rerank(
        self, question: str, chunks: Sequence[RetrievedChunk], top_n: int
    ) -> Generation[list[RetrievedChunk]]:
        sources = {f"S{index}": chunk for index, chunk in enumerate(chunks, start=1)}
        generation = await self._chat.generate(rerank_prompt(question, sources), RerankDraft)
        ranked: list[RetrievedChunk] = []
        for label in generation.value.source_ids:
            chunk = sources.get(label.strip())  # ids outside the prompt are ignored
            if chunk is not None and chunk not in ranked:
                ranked.append(chunk)
        return Generation(ranked[:top_n], generation.usage)
