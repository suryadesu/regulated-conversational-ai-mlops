"""OpenTelemetry tracing setup for the gateway."""

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_tracing(app: FastAPI, otlp_endpoint: str, service_name: str) -> None:
    """Configure OTLP trace export and FastAPI auto-instrumentation.

    The batch exporter connects lazily in the background, so an unreachable
    collector never blocks or fails app startup. No prompt or completion
    content is ever attached to spans.

    Args:
        app: FastAPI — the gateway application to instrument.
        otlp_endpoint: str — OTLP collector endpoint URL.
        service_name: str — resource service.name for emitted spans.
    """
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
