import uuid
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from fastapi.testclient import TestClient
from opentelemetry import _logs, trace
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.image import DockerImage

from app.adapters.postgres_documents import PostgresDocumentRepository
from app.adapters.postgres_retriever import PostgresRetriever
from app.application.ports import ChatModelPort, EmbeddingPort
from app.config import Settings
from app.main import create_app
from tests.chat_providers import PROVIDERS, Harness
from tests.factories import (
    CHAT_DOCUMENTS,
    EMBEDDING_DIMENSIONS,
    ISOLATED_APPLICATION_NAME,
    REQUIRED_ENV,
    ClientFactory,
    alembic_config,
    fixture_bytes,
    make_settings,
    psql,
)
from tests.fakes import FakeChatModel, FakeEmbeddings, KeywordEmbeddings, Reply
from tests.provider_stub import provider_stub

DB_IMAGE_DIR = Path(__file__).resolve().parents[2] / "db"


@pytest.fixture(scope="session")
def _span_exporter() -> InMemorySpanExporter:
    """Process-wide tracer provider: OpenTelemetry accepts set_tracer_provider only once."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))  # synchronous: spans visible at once
    trace.set_tracer_provider(provider)
    return exporter


@pytest.fixture(scope="session")
def _log_exporter() -> InMemoryLogRecordExporter:
    """Process-wide logger provider, so FastAPI's native telemetry would have somewhere to
    export logs (set_logger_provider is accepted only once)."""
    exporter = InMemoryLogRecordExporter()  # type: ignore[no-untyped-call]  # SDK class has no annotated __init__
    provider = LoggerProvider()
    provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
    _logs.set_logger_provider(provider)
    return exporter


@pytest.fixture
def exported_logs(_log_exporter: InMemoryLogRecordExporter) -> Iterator[InMemoryLogRecordExporter]:
    """Log records exported during this test only."""
    _log_exporter.clear()
    yield _log_exporter
    _log_exporter.clear()


@pytest.fixture
def spans(_span_exporter: InMemorySpanExporter) -> Iterator[InMemorySpanExporter]:
    """Finished spans of this test only: `spans.get_finished_spans()`."""
    _span_exporter.clear()
    yield _span_exporter
    _span_exporter.clear()


@pytest.fixture
def unreachable_settings() -> Settings:
    """Points at a closed port: the engine is created but every connection fails."""
    return make_settings("postgresql+asyncpg://cwyd:cwyd@127.0.0.1:1/cwyd")


@pytest.fixture
def settings_for() -> Callable[[str], Settings]:
    """Factory: Settings pointing at any database URL (e.g. a testcontainers instance)."""
    return make_settings


@pytest.fixture(scope="session")
def postgres() -> Iterator[PostgresContainer]:
    """PostgreSQL built from db/Dockerfile (runtime target), migrated to head.

    Synchronous on purpose: migrations/env.py runs its own event loop (asyncio.run).
    """
    with (
        DockerImage(path=DB_IMAGE_DIR, tag="cwyd-db:test", target="runtime") as image,
        PostgresContainer(str(image), driver="asyncpg") as container,
    ):
        psql(container, "CREATE DATABASE without_vector")
        command.upgrade(alembic_config(container.get_connection_url()), "head")
        yield container


@pytest.fixture(scope="session")
async def engine(postgres: PostgresContainer) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(postgres.get_connection_url())
    yield engine
    await engine.dispose()


@pytest.fixture
async def isolated_engine(postgres: PostgresContainer) -> AsyncIterator[AsyncEngine]:
    """A per-test engine tagged in pg_stat_activity, for tests that stall or kill connections."""
    engine = create_async_engine(
        postgres.get_connection_url(),
        connect_args={"server_settings": {"application_name": ISOLATED_APPLICATION_NAME}},
    )
    yield engine
    await engine.dispose()


@pytest.fixture
def repository(engine: AsyncEngine) -> PostgresDocumentRepository:
    return PostgresDocumentRepository(engine)


@pytest.fixture
def retriever(engine: AsyncEngine) -> PostgresRetriever:
    return PostgresRetriever(engine)


@pytest.fixture
def documents_client_for(postgres: PostgresContainer) -> Iterator[ClientFactory]:
    """Clients sharing one owner per test (isolation by owner_id, DOM-06)."""
    owner_id = uuid.uuid4()

    with ExitStack() as clients:

        def build(embeddings: EmbeddingPort | None = None, **overrides: Any) -> TestClient:
            settings = make_settings(
                postgres.get_connection_url(), default_owner_id=owner_id, **overrides
            )
            app = create_app(settings, embeddings or FakeEmbeddings(EMBEDDING_DIMENSIONS))
            return clients.enter_context(TestClient(app))

        yield build


@pytest.fixture
def chat_client_for(postgres: PostgresContainer) -> Iterator[ClientFactory]:
    """One owner per test (isolation by owner_id); documents uploaded on demand."""
    owner_id = uuid.uuid4()

    with ExitStack() as clients:

        def build(
            *replies: Reply,
            upload: bool = True,
            chat: ChatModelPort | None = None,
            **overrides: Any,
        ) -> TestClient:
            settings = make_settings(
                postgres.get_connection_url(), default_owner_id=owner_id, **overrides
            )
            app = create_app(
                settings, KeywordEmbeddings(EMBEDDING_DIMENSIONS), chat or FakeChatModel(*replies)
            )
            client = clients.enter_context(TestClient(app))
            if upload:
                for name in CHAT_DOCUMENTS:  # TestClient runs the indexing background task inline
                    body = fixture_bytes(name)
                    response = client.post("/documents", files={"file": (name, body)})
                    assert response.status_code in (200, 202)
            return client

        yield build


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Start every test from a clean environment, whatever the shell exports."""
    for name in (*REQUIRED_ENV, "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.fixture
def valid_env(env: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Every required variable set; tests override or remove only the one they are about."""
    for name, value in REQUIRED_ENV.items():
        env.setenv(name, value)
    return env


@pytest.fixture(params=PROVIDERS, ids=lambda p: p.name)
def harness(request: pytest.FixtureRequest) -> Iterator[Harness]:
    """One ChatModelPort contract harness per provider, backed by a local HTTP stub."""
    with provider_stub() as stub:
        yield Harness(request.param, stub)
