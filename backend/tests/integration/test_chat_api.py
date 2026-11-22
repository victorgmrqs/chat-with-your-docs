"""POST /chat end to end: real PostgreSQL, fixture documents, declared LLM fakes.

The expected-evidence cases come from tests/fixtures/rag_cases.json. The chat model is an
oracle fake: it reads the sources the pipeline actually put in the prompt and cites the ones
holding the case's expected passages. What is verified is the backend: retrieval surfaces
those passages from the real database, and citations resolve to the right file and page.
"""

import json
import re
import uuid
from collections.abc import Callable, Iterator
from html import unescape
from typing import Any

import pytest
from fastapi.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer

from app.application.ports import ChatModelPort, ChatPrompt
from app.application.prompts import AnswerDraft
from app.domain.answers import INSUFFICIENT_EVIDENCE_MESSAGE, ChatModelTimeout, ChatModelUnavailable
from app.main import create_app
from tests.factories import BACKEND_DIR, EMBEDDING_DIMENSIONS, fixture_bytes, make_settings
from tests.fakes import FakeChatModel, KeywordEmbeddings, Reply

pytestmark = pytest.mark.integration

CASES = {
    case["id"]: case
    for case in json.loads((BACKEND_DIR / "tests/fixtures/rag_cases.json").read_text())["cases"]
}
DOCUMENTS = ("remote-work-policy.pdf", "expense-policy.pdf", "parental-leave-policy.md")
_SOURCE = re.compile(r'<source id="(S\d+)"[^>]*>\n(.*?)\n</source>', re.DOTALL)

ClientFactory = Callable[..., TestClient]


def _sources(prompt: ChatPrompt) -> dict[str, str]:
    return {label: unescape(body) for label, body in _SOURCE.findall(prompt.user)}


def _oracle(case: dict[str, Any]) -> Callable[[ChatPrompt], AnswerDraft]:
    def reply(prompt: ChatPrompt) -> AnswerDraft:
        sources = _sources(prompt)

        def label_of(phrase: str) -> str | None:
            return next((label for label, body in sources.items() if phrase in body), None)

        if case["expected_outcome"] == "answered":
            labels = [label_of(s["passage_contains"]) for s in case["expected_sources"]]
            answer = " ".join(f"Claim [{label}]." for label in labels if label)
            return AnswerDraft(outcome="answered", answer=answer, closest_source_id=None)
        related = case["expected_related_passage"]["passage_contains"]
        return AnswerDraft(
            outcome="insufficient_evidence", answer="", closest_source_id=label_of(related)
        )

    return reply


@pytest.fixture
def client_for(postgres: PostgresContainer) -> Iterator[ClientFactory]:
    """One owner per test (isolation by owner_id); documents uploaded on demand."""
    owner_id = uuid.uuid4()
    clients: list[TestClient] = []

    def build(
        *replies: Reply, upload: bool = True, chat: ChatModelPort | None = None, **overrides: Any
    ) -> TestClient:
        settings = make_settings(
            postgres.get_connection_url(), default_owner_id=owner_id, **overrides
        )
        app = create_app(
            settings, KeywordEmbeddings(EMBEDDING_DIMENSIONS), chat or FakeChatModel(*replies)
        )
        client = TestClient(app).__enter__()
        clients.append(client)
        if upload:
            for name in DOCUMENTS:  # TestClient runs the indexing background task inline
                response = client.post("/documents", files={"file": (name, fixture_bytes(name))})
                assert response.status_code in (200, 202)
        return client

    yield build
    for client in clients:
        client.__exit__(None, None, None)


def _cited(body: dict[str, Any]) -> list[tuple[str, int | None]]:
    return [(s["filename"], s["page"]) for s in body["sources"]]


def test_chat_coworking_two_sources(client_for: ClientFactory) -> None:
    case = CASES["coworking_two_sources"]
    client = client_for(_oracle(case))

    response = client.post("/chat", json={"question": case["question"]})

    body = response.json()
    assert response.status_code == 200
    assert body["outcome"] == "answered"
    assert _cited(body) == [(s["filename"], s["page"]) for s in case["expected_sources"]]
    for source, expected in zip(body["sources"], case["expected_sources"], strict=True):
        assert expected["passage_contains"] in source["passage"]
    assert [s["number"] for s in body["sources"]] == [1, 2]
    assert body["answer"] == "Claim [1]. Claim [2]."
    assert (body["provider"], body["model"]) == ("fake", "fake-chat-model")


def test_chat_contractor_parental_leave_insufficient(client_for: ClientFactory) -> None:
    case = CASES["contractor_parental_leave"]
    client = client_for(_oracle(case))

    body = client.post("/chat", json={"question": case["question"]}).json()

    expected = case["expected_related_passage"]
    assert body["outcome"] == "insufficient_evidence"
    assert body["answer"] == INSUFFICIENT_EVIDENCE_MESSAGE
    assert body["sources"] == []
    assert body["related_passage"]["filename"] == expected["filename"]
    assert expected["heading_contains"] in body["related_passage"]["heading"]
    assert expected["passage_contains"] in body["related_passage"]["passage"]


def test_chat_exact_term_amount(client_for: ClientFactory) -> None:
    case = CASES["exact_term_amount"]
    client = client_for(_oracle(case))

    body = client.post("/chat", json={"question": case["question"]}).json()

    assert body["outcome"] == "answered"
    assert _cited(body) == [("expense-policy.pdf", 2)]


def test_chat_invented_citation_is_not_a_source(client_for: ClientFactory) -> None:
    invented = AnswerDraft(outcome="answered", answer="Two weeks [S99].", closest_source_id=None)
    client = client_for(invented)

    response = client.post(
        "/chat", json={"question": CASES["contractor_parental_leave"]["question"]}
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "insufficient_evidence"
    assert response.json()["sources"] == []


def test_chat_provider_timeout_is_technical_failure(client_for: ClientFactory) -> None:
    client = client_for(ChatModelTimeout())

    response = client.post("/chat", json={"question": "What is the coworking limit?"})

    assert response.status_code == 504
    assert response.json()["code"] == "chat_timeout"


def test_chat_provider_error_is_technical_failure(client_for: ClientFactory) -> None:
    client = client_for(ChatModelUnavailable())

    response = client.post("/chat", json={"question": "What is the coworking limit?"})

    assert response.status_code == 502
    assert response.json()["code"] == "chat_unavailable"


def test_chat_empty_question(client_for: ClientFactory) -> None:
    response = client_for(upload=False).post("/chat", json={"question": "  "})

    assert response.status_code == 400
    assert response.json()["code"] == "empty_question"


def test_chat_control_characters_are_removed(client_for: ClientFactory) -> None:
    case = CASES["exact_term_amount"]
    client = client_for(_oracle(case))

    response = client.post("/chat", json={"question": "Which policy mentions\u0000 US$ 250?"})

    assert response.status_code == 200
    assert response.json()["outcome"] == "answered"


def test_chat_question_too_long(client_for: ClientFactory) -> None:
    client = client_for(upload=False, question_max_chars=10)

    response = client.post("/chat", json={"question": "x" * 11})

    assert response.status_code == 400
    assert response.json()["code"] == "question_too_long"


def test_chat_no_ready_documents(client_for: ClientFactory) -> None:
    response = client_for(upload=False).post("/chat", json={"question": "Anything?"})

    assert response.status_code == 409
    assert response.json()["code"] == "no_ready_documents"
