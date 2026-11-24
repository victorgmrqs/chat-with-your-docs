"""FastAPI's native HTTP spans around the pipeline spans (CWYD-12); probes are not traced."""

from fastapi.testclient import TestClient
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter
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


def test_http_tracing_skips_health_probes_behind_the_api_prefix(
    unreachable_settings: Settings, spans: InMemorySpanExporter
) -> None:
    """CWYD-20: through the web server the path carries the /api root path."""
    with TestClient(create_app(settings=unreachable_settings)) as client:
        client.get("/health", headers={"X-Forwarded-Prefix": "/api"})

    assert spans.get_finished_spans() == ()


def test_http_tracing_root_span_is_the_request(
    unreachable_settings: Settings, spans: InMemorySpanExporter
) -> None:
    with TestClient(create_app(settings=unreachable_settings)) as client:
        client.post("/chat", json={"question": "   "})  # 400 before any pipeline span

    [root] = [span for span in spans.get_finished_spans() if span.parent is None]
    assert root.name == "POST /chat"
    assert (root.attributes or {})["http.response.status_code"] == 400


CLIENT_TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"


def test_otel_ignores_client_traceparent(
    unreachable_settings: Settings, spans: InMemorySpanExporter
) -> None:
    """CWYD-27: a public client cannot join our spans to its trace or force sampling."""
    with TestClient(create_app(settings=unreachable_settings)) as client:
        response = client.post(
            "/chat",
            json={"question": "   "},
            headers={
                "traceparent": f"00-{CLIENT_TRACE_ID}-00f067aa0ba902b7-01",
                "tracestate": "vendor=client",
            },
        )

    [root] = [span for span in spans.get_finished_spans() if span.parent is None]
    assert root.context is not None
    assert f"{root.context.trace_id:032x}" != CLIENT_TRACE_ID
    assert root.context.trace_state.get("vendor") is None
    assert response.headers["X-Request-ID"]  # DOM-23 unchanged


def test_telemetry_logs_disabled(
    unreachable_settings: Settings,
    spans: InMemorySpanExporter,
    exported_logs: InMemoryLogRecordExporter,
) -> None:
    """CWYD-27 (DOM-22): FastAPI's native telemetry exports no logs (they carry exception
    messages); its traces still export."""
    app = create_app(settings=unreachable_settings)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret detail")  # unhandled: the generic 500

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/boom").status_code == 500

    assert exported_logs.get_finished_logs() == ()
    assert [span.name for span in spans.get_finished_spans() if span.parent is None] == [
        "GET /boom"
    ]
