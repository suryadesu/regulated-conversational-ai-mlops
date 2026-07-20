"""OpenTelemetry tracing setup for the gateway."""

from fastapi import FastAPI


def setup_tracing(app: FastAPI, otlp_endpoint: str, service_name: str) -> None:
    """Configure OTLP trace export and FastAPI auto-instrumentation.

    Args:
        app: FastAPI — the gateway application to instrument.
        otlp_endpoint: str — OTLP collector endpoint URL.
        service_name: str — resource service.name for emitted spans.
    """
    raise NotImplementedError
