"""EmbeddingPort contract for the OpenAI adapter against a local HTTP stub (no network):
provider errors are classified as misconfiguration (DOM-25) or temporary (DOM-03)."""

import pytest
from pydantic import SecretStr

from app.adapters.openai_embeddings import OpenAIEmbeddingAdapter
from app.application.ports import EmbeddingMisconfigured, EmbeddingUnavailable
from tests.provider_stub import JsonReply, provider_stub

TEXT = "Coworking reimbursement is limited to US$ 250."


def _adapter(base_url: str) -> OpenAIEmbeddingAdapter:
    return OpenAIEmbeddingAdapter(
        model="text-embedding-3-small",
        api_key=SecretStr("sk-test"),
        dimensions=3,
        max_retries=0,
        timeout_seconds=5,
        base_url=f"{base_url}/v1",
    )


def _error(status: int, code: str) -> JsonReply:
    return JsonReply({"error": {"message": "provider text", "type": code, "code": code}}, status)


async def test_embed_documents_success_returns_one_vector_per_text() -> None:
    with provider_stub() as stub:
        stub.replies.append(
            JsonReply(
                {
                    "object": "list",
                    "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2, 0.3]}],
                    "model": "text-embedding-3-small",
                    "usage": {"prompt_tokens": 9, "total_tokens": 9},
                }
            )
        )

        vectors = await _adapter(stub.base_url).embed_documents([TEXT])

    assert vectors == [[0.1, 0.2, 0.3]]


@pytest.mark.parametrize(
    ("status", "code"),
    [(401, "invalid_api_key"), (403, "permission_denied"), (404, "model_not_found")],
)
async def test_embed_documents_rejected_key_or_model_raises_misconfigured(
    status: int, code: str
) -> None:
    with provider_stub() as stub:
        stub.replies.append(_error(status, code))

        with pytest.raises(EmbeddingMisconfigured) as raised:
            await _adapter(stub.base_url).embed_documents([TEXT])

    assert "provider text" not in str(raised.value)  # exception type only


@pytest.mark.parametrize(("status", "code"), [(429, "rate_limit_exceeded"), (500, "server_error")])
async def test_embed_documents_temporary_failure_raises_unavailable_only(
    status: int, code: str
) -> None:
    with provider_stub() as stub:
        stub.replies.append(_error(status, code))

        with pytest.raises(EmbeddingUnavailable) as raised:
            await _adapter(stub.base_url).embed_documents([TEXT])

    assert not isinstance(raised.value, EmbeddingMisconfigured)
