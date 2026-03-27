"""Vezir Observability — Sprint 15 OpenTelemetry integration.

Provides tracing, metrics, and structured logging for the EventBus
governance pipeline. All 28 event types have trace representation.
"""
from observability.otel_setup import init_otel
from observability.tracing import TracingHandler
from observability.meters import MetricsHandler
from observability.structured_logging import StructuredLogHandler

__all__ = ["init_otel", "TracingHandler", "MetricsHandler", "StructuredLogHandler"]
