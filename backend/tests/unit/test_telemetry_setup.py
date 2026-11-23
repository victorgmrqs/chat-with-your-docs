"""SDK setup from settings (app/adapters/telemetry.py). Never installs a global provider."""

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased

from app.adapters.telemetry import build_span_exporter, build_tracer_provider
from app.config import Settings


def test_telemetry_none_sets_up_nothing(unreachable_settings: Settings) -> None:
    assert unreachable_settings.otel_traces_exporter == "none"  # the default
    assert build_tracer_provider(unreachable_settings) is None


def test_telemetry_console_exporter(unreachable_settings: Settings) -> None:
    settings = unreachable_settings.model_copy(update={"otel_traces_exporter": "console"})

    assert isinstance(build_span_exporter(settings), ConsoleSpanExporter)


def test_telemetry_otlp_exporter_adds_traces_path(unreachable_settings: Settings) -> None:
    settings = unreachable_settings.model_copy(
        update={
            "otel_traces_exporter": "otlp",
            "otel_exporter_otlp_endpoint": "http://jaeger:4318/",
        }
    )

    exporter = build_span_exporter(settings)

    assert isinstance(exporter, OTLPSpanExporter)
    assert exporter._endpoint == "http://jaeger:4318/v1/traces"  # no public accessor


def test_telemetry_provider_uses_service_name_and_ratio(unreachable_settings: Settings) -> None:
    settings = unreachable_settings.model_copy(
        update={"otel_traces_exporter": "console", "otel_traces_sampler_arg": 0.25}
    )

    provider = build_tracer_provider(settings)

    assert provider is not None
    assert provider.resource.attributes["service.name"] == "cwyd-backend"
    assert isinstance(provider.sampler, ParentBased)
    description = provider.sampler.get_description()  # type: ignore[no-untyped-call]  # SDK lacks annotations
    assert "0.25" in description
    provider.shutdown()
