"""FastAPI's native HTTP spans around the pipeline spans (CWYD-12); probes are not traced."""

from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.config import Settings
from app.main import create_app


def test_http_tracing_skips_health_probes(
    unreachable_settings: Settings, spans: InMemorySpanExporter
) -> None:
    with TestClient(create_app(settings=unreachable_settings)) as client:
        client.get("/health")
        client.get("/health/ready")

    assert spans.get_finished_spans() == ()


def test_http_tracing_root_span_is_the_request(
    unreachable_settings: Settings, spans: InMemorySpanExporter
) -> None:
    with TestClient(create_app(settings=unreachable_settings)) as client:
        client.post("/chat", json={"question": "   "})  # 400 before any pipeline span

    [root] = [span for span in spans.get_finished_spans() if span.parent is None]
    assert root.name == "POST /chat"
    assert (root.attributes or {})["http.response.status_code"] == 400
