from __future__ import annotations

import os
import threading

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


_configure_lock = threading.Lock()
_configured = False


def configure_telemetry() -> None:
    global _configured
    if _configured:
        return
    with _configure_lock:
        if _configured:
            return
        current = trace.get_tracer_provider()
        if not isinstance(current, TracerProvider):
            provider = TracerProvider(resource=Resource.create({"service.name": "sme-ai-ops-agent"}))
            endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
            if endpoint:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
            trace.set_tracer_provider(provider)
        _configured = True


def get_tracer():
    configure_telemetry()
    return trace.get_tracer("sme-ai-ops-agent")
