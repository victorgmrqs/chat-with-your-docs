import pytest
from pydantic import SecretStr

from app.adapters.openai_embeddings import OpenAIEmbeddingAdapter
from app.application.ports import EmbeddingUnavailable


async def test_embed_documents_provider_unreachable_raises_embedding_unavailable() -> None:
    adapter = OpenAIEmbeddingAdapter(
        model="text-embedding-3-small",
        api_key=SecretStr("sk-test"),
        dimensions=8,
        max_retries=0,
        timeout_seconds=2,
        base_url="http://127.0.0.1:1/v1",  # closed port: connection refused, no network
    )

    with pytest.raises(EmbeddingUnavailable):
        await adapter.embed_documents(["Coworking reimbursement is limited to US$ 250."])
