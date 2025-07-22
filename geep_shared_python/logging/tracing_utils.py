from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from pydantic_settings import BaseSettings
from opentelemetry.sdk.resources import Resource


class TraceSettings(BaseSettings):
    tracing_url: str


def create_tracer(service_name: str) -> trace.Tracer:
    resource = Resource.create({"service.name": service_name})
    tracer = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer)

    span_exporter = OTLPSpanExporter()
    span_processor = BatchSpanProcessor(span_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)  # type: ignore
    # https://github.com/open-telemetry/opentelemetry-python/issues/2591#issuecomment-1403297872

    return tracer.get_tracer(__name__)
