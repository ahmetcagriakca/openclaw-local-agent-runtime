"""Prometheus metrics exporter API — B-117.

Exposes Vezir metrics in OpenMetrics/Prometheus format for Grafana scraping.
Reads from MetricStore and provides /metrics endpoint.
"""
import logging
import os
import time
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

logger = logging.getLogger("mcc.api.metrics")
router = APIRouter(tags=["metrics"])

_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
METRICS_PATH = _ROOT / "logs" / "metrics.json"
MISSION_HISTORY_PATH = _ROOT / "logs" / "mission-history.json"


def _collect_metrics() -> str:
    """Collect all metrics and format as Prometheus exposition text."""
    import json
    lines = []

    # Mission metrics from history
    missions_by_status = {}
    active_count = 0
    if MISSION_HISTORY_PATH.exists():
        try:
            with open(MISSION_HISTORY_PATH, "r", encoding="utf-8") as f:
                history = json.load(f)
            if isinstance(history, list):
                for m in history:
                    status = m.get("status", "unknown")
                    missions_by_status[status] = missions_by_status.get(status, 0) + 1
                    if status in ("running", "pending", "in_progress"):
                        active_count += 1
        except (json.JSONDecodeError, OSError):
            pass

    # vezir_missions_total
    lines.append("# HELP vezir_missions_total Total missions by status")
    lines.append("# TYPE vezir_missions_total gauge")
    for status, count in missions_by_status.items():
        lines.append(f'vezir_missions_total{{status="{status}"}} {count}')

    # vezir_missions_active
    lines.append("# HELP vezir_missions_active Currently active missions")
    lines.append("# TYPE vezir_missions_active gauge")
    lines.append(f"vezir_missions_active {active_count}")

    # Metric store metrics
    if METRICS_PATH.exists():
        try:
            with open(METRICS_PATH, "r", encoding="utf-8") as f:
                metrics_data = json.load(f)
            if isinstance(metrics_data, dict):
                for key, value in metrics_data.items():
                    if isinstance(value, (int, float)):
                        safe_key = key.replace(".", "_").replace("-", "_")
                        lines.append(f"vezir_{safe_key} {value}")
        except (json.JSONDecodeError, OSError):
            pass

    # Timestamp
    lines.append(f"# Generated at {time.time():.0f}")
    return "\n".join(lines) + "\n"


@router.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    return _collect_metrics()


@router.get("/metrics/json")
def metrics_json():
    """JSON format metrics for programmatic access."""
    import json

    missions_by_status = {}
    active_count = 0
    total_count = 0

    if MISSION_HISTORY_PATH.exists():
        try:
            with open(MISSION_HISTORY_PATH, "r", encoding="utf-8") as f:
                history = json.load(f)
            if isinstance(history, list):
                total_count = len(history)
                for m in history:
                    status = m.get("status", "unknown")
                    missions_by_status[status] = missions_by_status.get(status, 0) + 1
                    if status in ("running", "pending", "in_progress"):
                        active_count += 1
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "missions": {
            "total": total_count,
            "active": active_count,
            "by_status": missions_by_status,
        },
        "timestamp": time.time(),
    }
