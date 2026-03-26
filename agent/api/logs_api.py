"""Logs API — expose recent errors and audit trail for the dashboard."""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter(tags=["logs"])


class LogEntry(BaseModel):
    timestamp: str
    level: str
    source: str
    message: str


class LogsResponse(BaseModel):
    errors: list[LogEntry] = Field(default_factory=list)
    mutations: list[LogEntry] = Field(default_factory=list)
    totalErrors: int = 0
    totalMutations: int = 0


def _get_paths():
    from api.server import API_LOG_PATH, OC_ROOT
    telemetry_path = OC_ROOT / "logs" / "policy-telemetry.jsonl"
    return API_LOG_PATH, telemetry_path


@router.get("/logs/recent", response_model=LogsResponse)
async def get_recent_logs(limit: int = 50):
    """Return recent errors and mutation audit entries."""
    api_log_path, telemetry_path = _get_paths()

    errors: list[LogEntry] = []
    mutations: list[LogEntry] = []

    # 1. Parse API log for warnings/errors and mutation audits
    if api_log_path.exists():
        try:
            lines = api_log_path.read_text(encoding="utf-8").splitlines()
            for line in reversed(lines[-500:]):
                if len(errors) >= limit and len(mutations) >= limit:
                    break

                if "MUTATION_AUDIT" in line and len(mutations) < limit:
                    # Extract JSON from audit line
                    idx = line.find("{")
                    if idx >= 0:
                        try:
                            data = json.loads(line[idx:])
                            mutations.append(LogEntry(
                                timestamp=data.get("timestamp", ""),
                                level="INFO",
                                source="mutation",
                                message=f"{data.get('operation','')} {data.get('targetId','')} → {data.get('outcome','')}",
                            ))
                        except Exception:
                            pass

                elif ("WARNING" in line or "ERROR" in line) and len(errors) < limit:
                    # Parse log line: timestamp LEVEL logger: message
                    match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+) (\w+) (.+)", line)
                    if match:
                        errors.append(LogEntry(
                            timestamp=match.group(1),
                            level=match.group(2),
                            source="api",
                            message=match.group(3),
                        ))
        except Exception:
            pass

    # 2. Parse telemetry for stage_failed and mission_failed events
    if telemetry_path.exists():
        try:
            lines = telemetry_path.read_text(encoding="utf-8").splitlines()
            for line in reversed(lines[-500:]):
                if len(errors) >= limit:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    etype = ev.get("event", "")
                    if etype in ("stage_failed", "mission_failed"):
                        mid = ev.get("mission_id", "")
                        err = ev.get("error") or ev.get("failure_reason") or ""
                        errors.append(LogEntry(
                            timestamp=ev.get("timestamp", ""),
                            level="ERROR",
                            source=etype,
                            message=f"[{mid}] {err}" if mid else err,
                        ))
                except Exception:
                    continue
        except Exception:
            pass

    # Sort by timestamp descending
    errors.sort(key=lambda e: e.timestamp, reverse=True)
    mutations.sort(key=lambda e: e.timestamp, reverse=True)

    return LogsResponse(
        errors=errors[:limit],
        mutations=mutations[:limit],
        totalErrors=len(errors),
        totalMutations=len(mutations),
    )
