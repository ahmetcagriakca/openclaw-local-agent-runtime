# Jaeger Export Path — Evaluation Document

**Sprint 16 Task 16.20** — Document setup path, do not deploy.

## Can We Export OTel Traces to Jaeger?

**Yes.** The OpenTelemetry SDK we use (Sprint 15) supports OTLP export natively. Jaeger accepts OTLP gRPC on port 4317.

## Setup Path

### 1. Install OTLP Exporter

```bash
pip install opentelemetry-exporter-otlp-proto-grpc
```

### 2. Configure OTel Setup

In `agent/observability/otel_setup.py`, add an `"otlp"` export mode:

```python
elif export_to == "otlp":
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317"))
    )
```

### 3. Run Jaeger (Docker)

```bash
docker run -d --name jaeger \
  -p 16686:16686 \  # Jaeger UI
  -p 4317:4317 \    # OTLP gRPC
  jaegertracing/all-in-one:latest
```

### 4. View Traces

Open `http://localhost:16686`, select service "vezir-runtime", view trace waterfalls.

## Decision

**NOT deploying now.** Sprint 16 stores traces in JSON files and serves them via API. Jaeger deployment is Phase 6 infrastructure work.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Jaeger (Docker) | Industry standard, great UI | Requires Docker, external dependency |
| Grafana Tempo | Pairs with Grafana dashboards | More complex setup |
| JSON file store | No dependencies, already built | Limited query capability |

Current approach (JSON file + API) is sufficient for single-operator use. Jaeger becomes valuable when we need distributed tracing across services or multi-operator visibility.
