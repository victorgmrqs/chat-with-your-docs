"""ChatModelPort contract harness: each provider's stubbed HTTP payloads and adapter builder.

The local stub (tests/provider_stub.py) answers in the provider's wire format, so the real
adapter code runs offline. The `harness` fixture (tests/conftest.py) yields one Harness per
provider.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, SecretStr

from app.adapters.anthropic_chat import AnthropicChatAdapter
from app.adapters.langchain_chat import LangChainChatAdapter
from app.adapters.openai_chat import OpenAIChatAdapter
from app.application.prompts import AnswerDraft
from tests.provider_stub import JsonReply, ProviderStub


def _openai_body(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 0,
        "model": "gpt-test",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": json.dumps(payload)},
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def _anthropic_body(payload: dict[str, Any], schema: type[BaseModel]) -> dict[str, Any]:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-test",
        "content": [
            {"type": "tool_use", "id": "toolu_1", "name": schema.__name__, "input": payload}
        ],
        "stop_reason": "tool_use",
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }


TIMEOUT_SECONDS = 0.5


def _openai(base_url: str) -> LangChainChatAdapter:
    return OpenAIChatAdapter(
        "gpt-test",
        SecretStr("sk-test"),
        max_tokens=100,
        timeout_seconds=TIMEOUT_SECONDS,
        max_retries=0,
        base_url=f"{base_url}/v1",
    )


def _anthropic(base_url: str) -> LangChainChatAdapter:
    return AnthropicChatAdapter(
        "claude-test",
        SecretStr("sk-ant-test"),
        max_tokens=100,
        timeout_seconds=TIMEOUT_SECONDS,
        max_retries=0,
        base_url=base_url,
    )


REFUSAL_TEXT = "I cannot help with the Zephyr request."


def _openai_refusal() -> dict[str, Any]:
    body = _openai_body({})
    body["choices"][0]["message"] = {"role": "assistant", "content": None, "refusal": REFUSAL_TEXT}
    return body


def _anthropic_refusal() -> dict[str, Any]:
    body = _anthropic_body({}, AnswerDraft)
    body["content"] = [{"type": "text", "text": REFUSAL_TEXT}]
    body["stop_reason"] = "refusal"
    return body


@dataclass(frozen=True)
class Provider:
    name: str
    model: str
    path: str
    build: Callable[[str], LangChainChatAdapter]
    body: Callable[[dict[str, Any], type[BaseModel]], dict[str, Any]]
    refusal: Callable[[], dict[str, Any]]


PROVIDERS = [
    Provider(
        "openai",
        "gpt-test",
        "/v1/chat/completions",
        _openai,
        lambda p, _: _openai_body(p),
        _openai_refusal,
    ),
    Provider(
        "anthropic", "claude-test", "/v1/messages", _anthropic, _anthropic_body, _anthropic_refusal
    ),
]


@dataclass(frozen=True)
class Harness:
    provider: Provider
    stub: ProviderStub

    def reply(self, payload: dict[str, Any], schema: type[BaseModel] = AnswerDraft) -> None:
        self.stub.replies.append(JsonReply(self.provider.body(payload, schema)))

    def adapter(self) -> LangChainChatAdapter:
        return self.provider.build(self.stub.base_url)
