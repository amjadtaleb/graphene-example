from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as OTLPGRPCSpanExporter,
)
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.grpc import GrpcAioInstrumentorServer, GrpcAioInstrumentorClient
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor


from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
# from .otel_psycopg import PsycopgInstrumentor
# see https://github.com/open-telemetry/opentelemetry-python-contrib/issues/2486
# copied from:
# https://github.com/ibash/opentelemetry-python-contrib/blob/ibash/async_tracing_release/instrumentation/opentelemetry-instrumentation-psycopg/src/opentelemetry/instrumentation/psycopg/__init__.py


def setup_telemetry():
    """Configures OpenTelemetry for the application."""
    resource = Resource(attributes={"service.name": "wasmer-graphql"})
    provider = TracerProvider(resource=resource)
    trace_processor = BatchSpanProcessor(OTLPGRPCSpanExporter(endpoint="http://otel-collector:4317/v1/traces"))
    provider.add_span_processor(trace_processor)

    trace.set_tracer_provider(provider)

    # Instrument libraries
    DjangoInstrumentor().instrument()
    PsycopgInstrumentor().instrument()
    AsyncioInstrumentor().instrument()
    LoggingInstrumentor().instrument()
    GrpcAioInstrumentorServer().instrument()
    GrpcAioInstrumentorClient().instrument()
    HTTPXClientInstrumentor().instrument()
