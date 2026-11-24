"""EmbeddingPort contract for the OpenAI adapter against a local HTTP stub (no network): token
usage (DOM-24), batching, retries, timeout, and provider errors classified by type only as
misconfiguration (DOM-25) or temporary (DOM-03)."""

from typing import Any

import pytest
from pydantic import SecretStr

from app.adapters.openai_embeddings import OpenAIEmbeddingAdapter
from app.application.ports import EmbeddingMisconfigured, EmbeddingUnavailable
from app.domain.usage import TokenUsage
from tests.provider_stub import Hang, JsonReply, provider_stub

TEXT = "Coworking reimbursement is limited to US$ 250."
MODEL = "text-embedding-3-small"


def _adapter(base_url: str, **overrides: Any) -> OpenAIEmbeddingAdapter:
    options: dict[str, Any] = {"max_retries": 0, "timeout_seconds": 5, **overrides}
    return OpenAIEmbeddingAdapter(
        model=MODEL,
        api_key=SecretStr("sk-test"),
        dimensions=3,
        base_url=f"{base_url}/v1",
        **options,
    )


def _embeddings(vectors: list[list[float]], prompt_tokens: int | None) -> JsonReply:
    body: dict[str, Any] = {
        "object": "list",
        "data": [
            {"object": "embedding", "index": i, "embedding": vector}
            for i, vector in enumerate(vectors)
        ],
        "model": f"{MODEL}-2026",
    }
    if prompt_tokens is not None:
        body["usage"] = {"prompt_tokens": prompt_tokens, "total_tokens": prompt_tokens}
    return JsonReply(body)


def _error(status: int, code: str) -> JsonReply:
    return JsonReply({"error": {"message": "provider text", "type": code, "code": code}}, status)


async def test_embedding_port_contract_reports_token_usage() -> None:
    with provider_stub() as stub:
        stub.replies.append(_embeddings([[0.1, 0.2, 0.3]], prompt_tokens=9))

        generation = await _adapter(stub.base_url).embed_documents([TEXT])

    assert generation.value == [[0.1, 0.2, 0.3]]
    # The model the provider reported, input tokens only (DOM-24).
    assert generation.usage == (TokenUsage(f"{MODEL}-2026", input_tokens=9, output_tokens=0),)
    [request] = stub.requests
    assert request["path"] == "/v1/embeddings"
    assert request["body"]["model"] == MODEL
    assert request["body"]["dimensions"] == 3
    assert request["body"]["input"] == [TEXT]


async def test_embedding_port_contract_without_usage_reports_none() -> None:
    with provider_stub() as stub:
        stub.replies.append(_embeddings([[0.1, 0.2, 0.3]], prompt_tokens=None))

        generation = await _adapter(stub.base_url).embed_documents([TEXT])

    assert generation.usage == ()  # DOM-24: unknown, never 0


async def test_embedding_port_contract_keeps_input_order() -> None:
    reply = _embeddings([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], prompt_tokens=4)
    reply.body["data"].reverse()  # providers may return items out of order
    with provider_stub() as stub:
        stub.replies.append(reply)

        generation = await _adapter(stub.base_url).embed_documents(["first", "second"])

    assert generation.value == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]


async def test_embedding_port_contract_batches_inputs_and_sums_usage() -> None:
    with provider_stub() as stub:
        stub.replies.extend(
            [
                _embeddings([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], prompt_tokens=4),
                _embeddings([[0.0, 0.0, 1.0]], prompt_tokens=2),
            ]
        )

        generation = await _adapter(stub.base_url, max_batch_texts=2).embed_documents(
            ["one", "two", "three"]
        )

    assert [request["body"]["input"] for request in stub.requests] == [["one", "two"], ["three"]]
    assert generation.value == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    assert generation.usage == (TokenUsage(f"{MODEL}-2026", input_tokens=6, output_tokens=0),)


async def test_embedding_port_contract_batches_by_characters() -> None:
    with provider_stub() as stub:
        stub.replies.extend([_embeddings([[1.0, 0.0, 0.0]], 1), _embeddings([[0.0, 1.0, 0.0]], 1)])

        await _adapter(stub.base_url, max_batch_chars=8).embed_documents(["12345", "67890"])

    assert [request["body"]["input"] for request in stub.requests] == [["12345"], ["67890"]]


async def test_embedding_port_contract_partial_usage_reports_none() -> None:
    """A batch without usage makes the call's total unknown, never too low (DOM-24)."""
    with provider_stub() as stub:
        stub.replies.extend(
            [_embeddings([[1.0, 0.0, 0.0]], 4), _embeddings([[0.0, 1.0, 0.0]], None)]
        )

        generation = await _adapter(stub.base_url, max_batch_texts=1).embed_documents(["a", "b"])

    assert generation.usage == ()
    assert len(generation.value) == 2


async def test_embedding_port_contract_wrong_vector_count_raises_unavailable() -> None:
    with provider_stub() as stub:
        stub.replies.append(_embeddings([[1.0, 0.0, 0.0]], 4))  # one vector for two texts

        with pytest.raises(EmbeddingUnavailable) as raised:
            await _adapter(stub.base_url).embed_documents(["a", "b"])

    assert str(raised.value) == "EmbeddingCountMismatch"


@pytest.mark.parametrize(("status", "code"), [(429, "rate_limit_exceeded"), (500, "server_error")])
async def test_embedding_port_contract_retries_transient_errors(status: int, code: str) -> None:
    with provider_stub() as stub:
        stub.replies.extend([_error(status, code), _embeddings([[0.1, 0.2, 0.3]], 9)])

        generation = await _adapter(stub.base_url, max_retries=1).embed_documents([TEXT])

    assert len(stub.requests) == 2
    assert generation.value == [[0.1, 0.2, 0.3]]


async def test_embedding_port_contract_timeout_raises_unavailable() -> None:
    with provider_stub() as stub:
        stub.replies.append(Hang(seconds=2))

        with pytest.raises(EmbeddingUnavailable) as raised:
            await _adapter(stub.base_url, timeout_seconds=0.2).embed_documents([TEXT])

    assert not isinstance(raised.value, EmbeddingMisconfigured)
    assert str(raised.value) == "APITimeoutError"


@pytest.mark.parametrize(
    ("status", "code", "expected"),
    [
        (401, "invalid_api_key", EmbeddingMisconfigured),
        (403, "permission_denied", EmbeddingMisconfigured),
        (404, "model_not_found", EmbeddingMisconfigured),
        (429, "rate_limit_exceeded", EmbeddingUnavailable),
        (500, "server_error", EmbeddingUnavailable),
    ],
)
async def test_embedding_port_contract_maps_errors_by_type(
    status: int, code: str, expected: type[EmbeddingUnavailable]
) -> None:
    with provider_stub() as stub:
        stub.replies.append(_error(status, code))

        with pytest.raises(EmbeddingUnavailable) as raised:
            await _adapter(stub.base_url).embed_documents([TEXT])

    assert type(raised.value) is expected
    assert "provider text" not in str(raised.value)  # exception type only (DOM-22)
