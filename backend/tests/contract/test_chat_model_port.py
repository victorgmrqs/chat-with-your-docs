"""chat_model_port_contract: OpenAI and Anthropic adapters honour the same ChatModelPort.

Offline by default: a local stub server (tests/provider_stub.py) answers the providers' HTTP
endpoints with canned payloads, so the real adapter code (LangChain client, structured-output
parsing, error mapping) runs without network. With RUN_LIVE_TESTS=1 and the provider
keys/models set, the `live` tests run the same contract against the real APIs.
"""

import json
import logging
import os

import pytest
from pydantic import SecretStr

from app.adapters.anthropic_chat import AnthropicChatAdapter
from app.adapters.openai_chat import OpenAIChatAdapter
from app.application.ports import ChatModelPort, ChatPrompt
from app.application.prompts import AnswerDraft, RerankDraft
from app.domain.answers import ChatModelTimeout, ChatModelUnavailable
from tests.chat_providers import REFUSAL_TEXT, TIMEOUT_SECONDS, Harness
from tests.provider_stub import Hang, JsonReply

PRIVATE_QUESTION = "What is the coworking limit for project Zephyr?"
PROMPT = ChatPrompt(system="Answer with citations.", user=PRIVATE_QUESTION)
ANSWER = {"outcome": "answered", "answer": "US$ 250 [S1].", "closest_source_id": None}


async def test_chat_model_port_contract_answer_schema(harness: Harness) -> None:
    harness.reply(ANSWER)
    adapter: ChatModelPort = harness.adapter()

    result = await adapter.generate(PROMPT, AnswerDraft)

    assert result.value == AnswerDraft.model_validate(ANSWER)


async def test_chat_model_port_contract_reports_token_usage(harness: Harness) -> None:
    # DOM-24: the usage the provider reported, keyed by the model name it reported.
    harness.reply(ANSWER)

    result = await harness.adapter().generate(PROMPT, AnswerDraft)

    [usage] = result.usage
    assert usage.model.startswith(harness.provider.model)
    assert (usage.input_tokens, usage.output_tokens) == (10, 5)


async def test_chat_model_port_contract_rerank_schema(harness: Harness) -> None:
    harness.reply({"source_ids": ["S2", "S1"]}, RerankDraft)

    result = await harness.adapter().generate(PROMPT, RerankDraft)

    assert result.value.source_ids == ["S2", "S1"]


async def test_chat_model_port_contract_sends_system_and_user(harness: Harness) -> None:
    harness.reply(ANSWER)

    await harness.adapter().generate(PROMPT, AnswerDraft)

    [request] = harness.stub.requests
    assert request["path"] == harness.provider.path
    sent = json.dumps(request["body"])
    assert PROMPT.system in sent
    assert PRIVATE_QUESTION in sent


async def test_chat_model_port_contract_reports_provider_and_model(harness: Harness) -> None:
    adapter = harness.adapter()

    assert (adapter.provider, adapter.model) == (harness.provider.name, harness.provider.model)


async def test_chat_model_port_contract_timeout(harness: Harness) -> None:
    harness.stub.replies.append(Hang(seconds=TIMEOUT_SECONDS * 4))

    with pytest.raises(ChatModelTimeout):
        await harness.adapter().generate(PROMPT, AnswerDraft)


async def test_chat_model_port_contract_provider_error(harness: Harness) -> None:
    harness.stub.replies.append(JsonReply({"error": {"message": "boom"}}, status=500))

    with pytest.raises(ChatModelUnavailable):
        await harness.adapter().generate(PROMPT, AnswerDraft)


async def test_chat_model_port_contract_refusal(
    harness: Harness, caplog: pytest.LogCaptureFixture
) -> None:
    harness.stub.replies.append(JsonReply(harness.provider.refusal()))

    with (
        caplog.at_level(logging.WARNING, logger="app.adapters.langchain_chat"),
        pytest.raises(ChatModelUnavailable),
    ):
        await harness.adapter().generate(PROMPT, AnswerDraft)

    logged = " ".join(r.getMessage() + repr(r.__dict__) for r in caplog.records)
    assert caplog.records
    assert REFUSAL_TEXT not in logged


async def test_chat_model_port_contract_invalid_structured_output(harness: Harness) -> None:
    harness.reply({"outcome": "maybe", "answer": 3})

    with pytest.raises(ChatModelUnavailable):
        await harness.adapter().generate(PROMPT, AnswerDraft)


async def test_chat_model_port_contract_failure_log_has_no_content(
    harness: Harness, caplog: pytest.LogCaptureFixture
) -> None:
    harness.stub.replies.append(JsonReply({"error": {"message": PRIVATE_QUESTION}}, status=500))

    with (
        caplog.at_level(logging.WARNING, logger="app.adapters.langchain_chat"),
        pytest.raises(ChatModelUnavailable),
    ):
        await harness.adapter().generate(PROMPT, AnswerDraft)

    logged = " ".join(r.getMessage() + repr(r.__dict__) for r in caplog.records)
    assert caplog.records
    assert PRIVATE_QUESTION not in logged


LIVE = os.environ.get("RUN_LIVE_TESTS") == "1"


_LIVE_ADAPTERS = {
    "openai": ("OPENAI_API_KEY", "LIVE_OPENAI_CHAT_MODEL", OpenAIChatAdapter),
    "anthropic": ("ANTHROPIC_API_KEY", "LIVE_ANTHROPIC_CHAT_MODEL", AnthropicChatAdapter),
}


def _live_adapter(name: str) -> ChatModelPort:
    key_env, model_env, adapter = _LIVE_ADAPTERS[name]
    key, model = os.environ.get(key_env), os.environ.get(model_env)
    if not (key and model):
        pytest.skip(f"{name}: set {key_env} and {model_env}")
    return adapter(model, SecretStr(key), max_tokens=300, timeout_seconds=30, max_retries=1)


@pytest.mark.live
@pytest.mark.skipif(not LIVE, reason="set RUN_LIVE_TESTS=1 to call the real providers")
@pytest.mark.parametrize("name", ["openai", "anthropic"])
async def test_chat_model_port_contract_live(name: str) -> None:
    prompt = ChatPrompt(
        system="Answer only from the sources and cite them as [S1].",
        user=(
            '<sources>\n<source id="S1" file="expense-policy.pdf" location="page 2">\n'
            "Coworking reimbursement is limited to US$ 250 per month per employee.\n"
            "</source>\n</sources>\n\n<question>\nWhat is the coworking limit?\n</question>"
        ),
    )

    result = await _live_adapter(name).generate(prompt, AnswerDraft)

    assert result.value.outcome == "answered"
    assert "[S1]" in result.value.answer
    assert result.usage  # DOM-24: real providers report token usage
