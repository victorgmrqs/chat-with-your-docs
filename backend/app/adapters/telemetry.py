"""OpenTelemetry SDK setup: the only module that knows about exporters (CWYD-12).

Switching the tracing backend (Jaeger, a collector, a vendor) is configuration only:
OTEL_TRACES_EXPORTER and OTEL_EXPORTER_OTLP_ENDPOINT.
"""

from opentelemetry import propagate, trace
from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.propagators.textmap import (
    CarrierT,
    Getter,
    Setter,
    TextMapPropagator,
    default_getter,
    default_setter,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from app.config import Settings

OTLP_TRACES_PATH = "/v1/traces"


def build_span_exporter(settings: Settings) -> SpanExporter | None:
    """None for `none`: tracing stays the API's no-op."""
    match settings.otel_traces_exporter:
        case "console":
            return ConsoleSpanExporter()
        case "otlp":
            # An explicit endpoint is used as is by the SDK: add the signal path here.
            base = settings.otel_exporter_otlp_endpoint.rstrip("/")
            return OTLPSpanExporter(endpoint=f"{base}{OTLP_TRACES_PATH}")
        case "none":
            return None


def build_tracer_provider(settings: Settings) -> TracerProvider | None:
    exporter = build_span_exporter(settings)
    if exporter is None:
        return None
    provider = TracerProvider(
        resource=Resource.create({SERVICE_NAME: settings.otel_service_name}),
        sampler=ParentBased(TraceIdRatioBased(settings.otel_traces_sampler_arg)),
    )
    # Batched and off the request path: an unreachable collector never slows a request.
    provider.add_span_processor(BatchSpanProcessor(exporter))
    return provider


class _NoPropagation(TextMapPropagator):
    """Extracts an empty context (a new trace, sampled by our own sampler) and injects nothing."""

    def extract(
        self,
        carrier: CarrierT,
        context: Context | None = None,
        getter: Getter[CarrierT] = default_getter,
    ) -> Context:
        return Context()

    def inject(
        self,
        carrier: CarrierT,
        context: Context | None = None,
        setter: Setter[CarrierT] = default_setter,
    ) -> None:
        return None

    @property
    def fields(self) -> set[str]:
        return set()


def ignore_client_trace_context() -> None:
    """The API is public: incoming traceparent, tracestate and baggage are not extracted, so a
    client cannot join our spans to its trace or force sampling; every request starts a new
    trace (CWYD-27). X-Request-ID is separate and unchanged (DOM-23)."""
    propagate.set_global_textmap(_NoPropagation())


def configure_tracing(settings: Settings) -> TracerProvider | None:
    """Install the process-wide provider; the caller shuts it down (flushes) on exit.

    OpenTelemetry accepts one provider per process: a second call is ignored with a warning.
    """
    ignore_client_trace_context()
    provider = build_tracer_provider(settings)
    if provider is not None:
        trace.set_tracer_provider(provider)
    return provider
