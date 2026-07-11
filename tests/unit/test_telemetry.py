from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.telemetry import get_tracer


def test_telemetry_records_span_attributes():
    exporter = InMemorySpanExporter()
    tracer = get_tracer()
    provider = trace.get_tracer_provider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    with tracer.start_as_current_span("test.span") as span:
        span.set_attribute("request.id", "req-123")
    finished = exporter.get_finished_spans()
    assert finished[-1].name == "test.span"
    assert finished[-1].attributes["request.id"] == "req-123"
