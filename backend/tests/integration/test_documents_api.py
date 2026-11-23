"""The ingestion scenarios through HTTP: real PostgreSQL, declared embedding fakes."""

import asyncio
import logging
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.community.postgres import PostgresContainer

from app.application import telemetry as t
from app.config import Settings
from app.main import create_app
from tests.factories import (
    EMBEDDING_DIMENSIONS,
    ClientFactory,
    StoredChunk,
    fixture_bytes,
    stored_chunks,
)
from tests.fakes import FailingEmbeddings, FakeEmbeddings, MisconfiguredEmbeddings

pytestmark = pytest.mark.integration


def _upload(client: TestClient, filename: str, content: bytes | None = None) -> Any:
    body = fixture_bytes(filename) if content is None else content
    return client.post("/documents", files={"file": (filename, body)})


def _stored_chunks(postgres: PostgresContainer, document_id: str) -> list[str]:
    """Database state, not the API view: `filename|page|heading|text` per chunk."""

    async def fetch() -> list[StoredChunk]:
        engine = create_async_engine(postgres.get_connection_url())
        try:
            return await stored_chunks(engine, uuid.UUID(document_id))
        finally:
            await engine.dispose()

    # Sync test (TestClient): no event loop is running here.
    return [
        f"{c.filename}|{c.page or ''}|{c.heading or ''}|{'text' if c.text else 'EMPTY'}"
        for c in asyncio.run(fetch())
    ]


def test_document_ingestion_success(
    documents_client_for: ClientFactory, postgres: PostgresContainer
) -> None:
    client = documents_client_for()

    accepted = [_upload(client, name) for name in ("remote-work-policy.pdf", "expense-policy.pdf")]
    # TestClient runs background tasks before returning: indexing is already finished.
    documents = [client.get(f"/documents/{a.json()['id']}").json() for a in accepted]

    assert [a.status_code for a in accepted] == [202, 202]
    assert [d["status"] for d in documents] == ["ready", "ready"]
    assert _stored_chunks(postgres, documents[0]["id"]) == [
        "remote-work-policy.pdf|1||text",
        "remote-work-policy.pdf|2||text",
    ]
    assert _stored_chunks(postgres, documents[1]["id"]) == [
        "expense-policy.pdf|1||text",
        "expense-policy.pdf|2||text",
    ]
    assert len(client.get("/documents").json()) == 2  # both stay available


def test_document_ingestion_markdown_and_text(
    documents_client_for: ClientFactory, postgres: PostgresContainer
) -> None:
    client = documents_client_for()

    markdown = _upload(client, "parental-leave-policy.md").json()
    text = _upload(client, "office-handbook.txt").json()

    assert (
        "parental-leave-policy.md||Parental Leave Policy > Eligibility > Full-time employees|text"
        in (_stored_chunks(postgres, markdown["id"]))
    )
    assert _stored_chunks(postgres, text["id"]) == ["office-handbook.txt|||text"]


def test_document_ingestion_unsupported_type(documents_client_for: ClientFactory) -> None:
    response = _upload(documents_client_for(), "unsupported.docx")

    assert response.status_code == 415
    assert response.json()["code"] == "unsupported_type"
    assert ".pdf" in response.json()["detail"]


def test_document_ingestion_empty_file(documents_client_for: ClientFactory) -> None:
    response = _upload(documents_client_for(), "empty.txt", b"")

    assert response.status_code == 400
    assert response.json()["code"] == "empty_file"


def test_document_ingestion_file_too_large(documents_client_for: ClientFactory) -> None:
    response = _upload(documents_client_for(max_upload_mb=1), "big.txt", b"a" * (1024 * 1024 + 1))

    assert response.status_code == 413
    assert response.json()["code"] == "file_too_large"


def test_ingestion_body_over_limit(documents_client_for: ClientFactory) -> None:
    """DOM-26: a direct API upload over MAX_UPLOAD_MB + 1 MB is cut off by the middleware."""
    client = documents_client_for(max_upload_mb=1)

    response = _upload(client, "big.txt", b"a" * (3 * 1024 * 1024))

    assert response.status_code == 413
    assert response.json()["code"] == "file_too_large"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert client.get("/documents").json() == []


def test_ingestion_body_over_limit_without_content_length(
    documents_client_for: ClientFactory,
) -> None:
    client = documents_client_for(max_upload_mb=1)

    def chunked_body() -> Iterator[bytes]:  # no Content-Length: counted as it streams
        yield b'--b\r\nContent-Disposition: form-data; name="file"; filename="big.txt"\r\n\r\n'
        for _ in range(12):
            yield b"a" * (256 * 1024)
        yield b"\r\n--b--\r\n"

    response = client.post(
        "/documents",
        content=chunked_body(),
        headers={"Content-Type": "multipart/form-data; boundary=b"},
    )

    assert response.status_code == 413
    assert response.json()["code"] == "file_too_large"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_ingestion_dimension_mismatch(documents_client_for: ClientFactory) -> None:
    """DOM-26: EMBEDDING_DIMENSIONS differs from vector(1536): readiness and uploads say so."""
    client = documents_client_for(embedding_dimensions=EMBEDDING_DIMENSIONS + 1)

    ready = client.get("/health/ready")
    upload = _upload(client, "office-handbook.txt")

    assert ready.status_code == 503
    assert ready.json() == {"detail": "embedding dimension mismatch"}
    assert upload.status_code == 503
    assert upload.json()["code"] == "embedding_dimension_mismatch"
    assert "EMBEDDING_DIMENSIONS" in upload.json()["detail"]
    assert client.get("/documents").json() == []  # nothing stored


def test_ingestion_dimension_mismatch_logged_at_startup(
    documents_client_for: ClientFactory, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR, logger="app.main"):
        documents_client_for(embedding_dimensions=EMBEDDING_DIMENSIONS + 1)

    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert [r.getMessage() for r in errors] == [
        f"Embedding dimension mismatch: EMBEDDING_DIMENSIONS={EMBEDDING_DIMENSIONS + 1}, "
        f"chunks.embedding={EMBEDDING_DIMENSIONS}"
    ]


def test_document_ingestion_traced_inside_the_upload_request(
    documents_client_for: ClientFactory, spans: InMemorySpanExporter
) -> None:
    # CWYD-12: the background job runs after the 202, inside the upload's trace.
    client = documents_client_for()

    accepted = _upload(client, "office-handbook.txt")

    finished = {span.name: span for span in spans.get_finished_spans()}
    http, ingest = finished["POST /documents"], finished[t.INGEST]
    assert http.parent is None
    assert ingest.context is not None
    assert http.context is not None
    assert ingest.context.trace_id == http.context.trace_id
    attributes = ingest.attributes or {}
    assert attributes[t.DOCUMENT_ID] == accepted.json()["id"]
    assert attributes[t.DOCUMENT_STATUS] == "ready"


def test_document_ingestion_no_extractable_text(documents_client_for: ClientFactory) -> None:
    client = documents_client_for()

    accepted = _upload(client, "scanned-notice.pdf")
    document = client.get(f"/documents/{accepted.json()['id']}").json()

    assert document["status"] == "failed"
    assert document["failure_reason"] == "no_extractable_text"
    assert "selectable text" in document["failure_message"]
    assert document["can_retry"] is False


def test_document_ingestion_indexing_failure(documents_client_for: ClientFactory) -> None:
    client = documents_client_for(FailingEmbeddings())

    accepted = _upload(client, "expense-policy.pdf")
    document = client.get(f"/documents/{accepted.json()['id']}").json()

    assert document["status"] == "failed"
    assert document["failure_reason"] == "indexing_failed"
    assert "Upload the same file again" in document["failure_message"]


def test_document_ingestion_provider_misconfigured(documents_client_for: ClientFactory) -> None:
    client = documents_client_for(MisconfiguredEmbeddings())

    accepted = _upload(client, "expense-policy.pdf")
    document = client.get(f"/documents/{accepted.json()['id']}").json()

    assert document["status"] == "failed"
    assert document["failure_reason"] == "provider_misconfigured"
    assert "EMBEDDING_MODEL" in document["failure_message"]
    assert document["can_retry"] is True


def test_document_ingestion_retry_after_provider_misconfigured(
    documents_client_for: ClientFactory,
) -> None:
    failed = _upload(documents_client_for(MisconfiguredEmbeddings()), "expense-policy.pdf").json()
    client = documents_client_for()  # the operator fixed the key or model

    retried = _upload(client, "expense-policy.pdf")
    document = client.get(f"/documents/{failed['id']}").json()

    assert retried.status_code == 202
    assert retried.json()["id"] == failed["id"]
    assert document["status"] == "ready"


def test_document_ingestion_duplicate_upload(documents_client_for: ClientFactory) -> None:
    client = documents_client_for()
    first = _upload(client, "remote-work-policy.pdf")

    second = _upload(client, "remote-work-policy-copy.pdf", fixture_bytes("remote-work-policy.pdf"))

    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["status"] == "ready"
    assert [d["id"] for d in client.get("/documents").json()] == [first.json()["id"]]


def test_document_ingestion_retry_after_indexing_failure(
    documents_client_for: ClientFactory,
) -> None:
    failed = _upload(documents_client_for(FailingEmbeddings()), "expense-policy.pdf").json()
    client = documents_client_for()

    retried = _upload(client, "expense-policy.pdf")
    document = client.get(f"/documents/{failed['id']}").json()

    assert retried.status_code == 202
    assert retried.json()["id"] == failed["id"]
    assert document["status"] == "ready"


def test_document_ingestion_unknown_document(documents_client_for: ClientFactory) -> None:
    response = documents_client_for().get(f"/documents/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["code"] == "document_not_found"


def test_documents_api_database_unavailable(unreachable_settings: Settings) -> None:
    app = create_app(unreachable_settings, FakeEmbeddings(EMBEDDING_DIMENSIONS))

    with TestClient(app) as client:  # starts: recovery at startup is best effort
        listed = client.get("/documents")
        uploaded = _upload(client, "office-handbook.txt")

    assert listed.status_code == 503
    body = listed.json()
    assert (body["code"], body["detail"]) == ("database_unavailable", "database unavailable")
    assert body["request_id"] == listed.headers["X-Request-ID"]  # DOM-23
    assert uploaded.status_code == 503
