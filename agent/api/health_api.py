"""Health and capabilities API — comprehensive system status."""
import glob
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request

from api.schemas import (
    HealthResponse, ComponentHealth, CapabilitiesResponse,
    ResponseMeta, DataQuality,
)

router = APIRouter(tags=["health"])


def _check_services_json() -> dict:
    """Read services.json for registered services and heartbeat status."""
    from api.server import SERVICES_PATH
    if not SERVICES_PATH.exists():
        return {}
    try:
        return json.loads(SERVICES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _count_missions() -> dict:
    """Count missions by state."""
    from api.server import MISSIONS_DIR
    counts = {"total": 0, "active": 0, "completed": 0, "failed": 0, "pending": 0}
    pattern = str(MISSIONS_DIR / "mission-*.json")
    for fpath in glob.glob(pattern):
        base = os.path.basename(fpath)
        if "-state.json" in base or "-summary.json" in base:
            continue
        counts["total"] += 1
        try:
            data = json.loads(Path(fpath).read_text(encoding="utf-8"))
            status = data.get("status", "unknown")
            # Check state file for accurate status
            mid = data.get("missionId", "")
            state_path = MISSIONS_DIR / f"{mid}-state.json"
            if state_path.exists():
                try:
                    sd = json.loads(state_path.read_text(encoding="utf-8"))
                    status = sd.get("status", status)
                except Exception:
                    pass
            if status in ("completed",):
                counts["completed"] += 1
            elif status in ("failed", "aborted", "timed_out"):
                counts["failed"] += 1
            elif status in ("pending",):
                counts["pending"] += 1
            elif status in ("planning", "executing", "gate_check", "rework", "approval_wait"):
                counts["active"] += 1
        except Exception:
            pass
    return counts


def _count_approvals() -> dict:
    """Count approvals by status."""
    from api.server import APPROVALS_DIR
    counts = {"total": 0, "pending": 0, "approved": 0, "denied": 0}
    if not APPROVALS_DIR.exists():
        return counts
    for fpath in APPROVALS_DIR.glob("apv-*.json"):
        counts["total"] += 1
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            status = data.get("status", "unknown")
            if status == "pending":
                counts["pending"] += 1
            elif status in ("approved",):
                counts["approved"] += 1
            elif status in ("denied", "timeout"):
                counts["denied"] += 1
        except Exception:
            pass
    return counts


def _check_log_size() -> dict:
    """Check log file sizes."""
    from api.server import API_LOG_PATH, MISSIONS_DIR, TELEMETRY_PATH
    result = {}
    for name, path in [("api_log", API_LOG_PATH), ("telemetry", TELEMETRY_PATH)]:
        try:
            size = os.path.getsize(str(path)) if Path(path).exists() else 0
            result[name] = f"{size / 1024:.0f}KB" if size < 1024 * 1024 else f"{size / (1024*1024):.1f}MB"
        except Exception:
            result[name] = "unknown"
    # Count mission files
    try:
        mission_files = len(list(MISSIONS_DIR.glob("*.json")))
        result["mission_files"] = str(mission_files)
    except Exception:
        result["mission_files"] = "unknown"
    return result


@router.get("/health", response_model=HealthResponse)
async def get_health(request: Request):
    from api.server import normalizer, capability_checker, PORT

    now = datetime.now(timezone.utc).isoformat()
    components = {}

    # 1. API server
    components["api"] = ComponentHealth(
        name="Mission Control API", status="ok",
        detail=f"serving on :{PORT}, PID {os.getpid()}", lastCheckAt=now)

    # 2. Cache
    if normalizer:
        cs = normalizer.get_cache_stats()
        cache_status = "ok" if cs.errors < cs.hits else "degraded" if cs.entries > 0 else "ok"
        components["cache"] = ComponentHealth(
            name="File Cache", status=cache_status,
            detail=f"entries={cs.entries}, hits={cs.hits}, errors={cs.errors}",
            lastCheckAt=now)
    else:
        components["cache"] = ComponentHealth(
            name="File Cache", status="error", detail="not initialized")

    # 3. Capabilities
    if capability_checker:
        ms = capability_checker.get_manifest_status()
        cap_status = "ok" if ms == "ok" else ("degraded" if ms == "degraded" else "unknown")
        all_caps = capability_checker.get_all() if capability_checker else {}
        avail = sum(1 for c in all_caps.values() if c.status.value == "available")
        components["capabilities"] = ComponentHealth(
            name="Capability Manifest", status=cap_status,
            detail=f"{avail}/{len(all_caps)} available", lastCheckAt=now)
    else:
        components["capabilities"] = ComponentHealth(
            name="Capability Manifest", status="error", detail="not initialized")

    # 4. SSE Manager
    try:
        sse_mgr = getattr(request.app.state, "sse_manager", None)
        if sse_mgr:
            client_count = len(sse_mgr._clients) if hasattr(sse_mgr, '_clients') else 0
            max_clients = getattr(sse_mgr, '_max_clients', 10)
            sse_status = "ok" if client_count < max_clients else "degraded"
            components["sse"] = ComponentHealth(
                name="SSE Manager", status=sse_status,
                detail=f"{client_count}/{max_clients} clients connected",
                lastCheckAt=now)
        else:
            components["sse"] = ComponentHealth(
                name="SSE Manager", status="error", detail="not initialized")
    except Exception:
        components["sse"] = ComponentHealth(
            name="SSE Manager", status="unknown", detail="unable to check")

    # 5. File Watcher (check via services.json heartbeat)
    services = _check_services_json()
    api_svc = services.get("mission-control-api", {})
    if api_svc:
        hb = api_svc.get("lastHeartbeatAt", "")
        started = api_svc.get("startedAt", "")
        if hb:
            try:
                hb_time = datetime.fromisoformat(hb)
                age_s = (datetime.now(timezone.utc) - hb_time).total_seconds()
                hb_status = "ok" if age_s < 60 else "degraded"
                # Calculate uptime
                if started:
                    start_time = datetime.fromisoformat(started)
                    uptime_s = (datetime.now(timezone.utc) - start_time).total_seconds()
                    if uptime_s < 3600:
                        uptime_str = f"{uptime_s/60:.0f}m"
                    else:
                        uptime_str = f"{uptime_s/3600:.1f}h"
                else:
                    uptime_str = "unknown"
                components["heartbeat"] = ComponentHealth(
                    name="Service Heartbeat", status=hb_status,
                    detail=f"last: {int(age_s)}s ago, uptime: {uptime_str}",
                    lastCheckAt=hb)
            except Exception:
                pass

    # 6. Mission Stats
    mission_counts = _count_missions()
    m_status = "ok"
    if mission_counts["failed"] > mission_counts["completed"] and mission_counts["total"] > 0:
        m_status = "degraded"
    components["missions"] = ComponentHealth(
        name="Missions", status=m_status,
        detail=(f"total={mission_counts['total']}, active={mission_counts['active']}, "
                f"completed={mission_counts['completed']}, failed={mission_counts['failed']}, "
                f"pending={mission_counts['pending']}"),
        lastCheckAt=now)

    # 7. Approval Stats
    approval_counts = _count_approvals()
    a_status = "ok"
    if approval_counts["pending"] > 0:
        a_status = "degraded"
    components["approvals"] = ComponentHealth(
        name="Approvals", status=a_status,
        detail=(f"total={approval_counts['total']}, pending={approval_counts['pending']}, "
                f"approved={approval_counts['approved']}, denied={approval_counts['denied']}"),
        lastCheckAt=now)

    # 8. Log / Storage
    log_info = _check_log_size()
    components["storage"] = ComponentHealth(
        name="Storage", status="ok",
        detail=(f"API log: {log_info['api_log']}, telemetry: {log_info['telemetry']}, "
                f"mission files: {log_info['mission_files']}"),
        lastCheckAt=now)

    # 9. LLM Providers (check env vars)
    providers = []
    if os.environ.get("OPENAI_API_KEY"):
        providers.append("OpenAI")
    if os.environ.get("ANTHROPIC_API_KEY"):
        providers.append("Anthropic")
    if os.environ.get("OLLAMA_URL") or os.environ.get("OLLAMA_HOST"):
        providers.append("Ollama")
    prov_status = "ok" if providers else "error"
    components["llm_providers"] = ComponentHealth(
        name="LLM Providers", status=prov_status,
        detail=", ".join(providers) if providers else "No API keys configured (OPENAI_API_KEY, ANTHROPIC_API_KEY)",
        lastCheckAt=now)

    # Overall status
    statuses = [c.status for c in components.values()]
    overall = ("error" if "error" in statuses
               else "degraded" if "degraded" in statuses else "ok")

    meta = ResponseMeta(dataQuality=DataQuality.FRESH)
    return HealthResponse(meta=meta, status=overall, components=components)


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def list_capabilities():
    from api.server import capability_checker
    caps = capability_checker.get_all() if capability_checker else {}
    meta = ResponseMeta(dataQuality=DataQuality.FRESH)
    return CapabilitiesResponse(meta=meta, capabilities=caps)
