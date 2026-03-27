"""OTel Setup — TracerProvider + MeterProvider initialization.

Task 15.0: Configures OpenTelemetry exporters for Vezir runtime.
Console exporter for dev, OTLP for prod (future).
"""
from __future__ import annotations

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    InMemoryMetricReader,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

SERVICE_NAME = "vezir-runtime"


def init_otel(
    service_name: str = SERVICE_NAME,
    export_to: str = "console",
) -> tuple[trace.Tracer, metrics.Meter]:
    """Initialize OpenTelemetry TracerProvider + MeterProvider.

    Args:
        service_name: OTel service name attribute.
        export_to: "console" for dev, "memory" for testing, "none" for silent.

    Returns:
        (tracer, meter) tuple ready for use.
    """
    resource = Resource.create({"service.name": service_name})

    # ── Traces ────────────────────────────────────────────────
    tracer_provider = TracerProvider(resource=resource)

    if export_to == "console":
        tracer_provider.add_span_processor(
            SimpleSpanProcessor(ConsoleSpanExporter())
        )
    # "memory" and "none" get no exporter — spans still recorded in-process

    trace.set_tracer_provider(tracer_provider)

    # ── Metrics ───────────────────────────────────────────────
    if export_to == "memory":
        reader = InMemoryMetricReader()
    elif export_to == "console":
        reader = PeriodicExportingMetricReader(
            ConsoleMetricExporter(), export_interval_millis=30000
        )
    else:
        reader = InMemoryMetricReader()

    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)

    tracer = trace.get_tracer(service_name)
    meter = metrics.get_meter(service_name)

    return tracer, meter


def shutdown_otel() -> None:
    """Flush and shut down providers. Call at process exit."""
    provider = trace.get_tracer_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()

    meter_provider = metrics.get_meter_provider()
    if hasattr(meter_provider, "shutdown"):
        meter_provider.shutdown()
