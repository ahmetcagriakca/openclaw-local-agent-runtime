"""Health and capabilities API — GPT Fix 3+4: wrapper + ComponentHealth.name."""
from datetime import datetime, timezone

from fastapi import APIRouter

from api.schemas import (
    HealthResponse, ComponentHealth, CapabilitiesResponse,
    ResponseMeta, DataQuality,
)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health():
    from api.server import normalizer, capability_checker

    now = datetime.now(timezone.utc).isoformat()
    components = {}

    components["api"] = ComponentHealth(
        name="api", status="ok", detail="serving", lastCheckAt=now)

    if normalizer:
        cs = normalizer.get_cache_stats()
        components["cache"] = ComponentHealth(
            name="cache", status="ok",
            detail=f"entries={cs.entries}, hits={cs.hits}, errors={cs.errors}",
            lastCheckAt=now)
    else:
        components["cache"] = ComponentHealth(
            name="cache", status="error", detail="not initialized")

    if capability_checker:
        ms = capability_checker.get_manifest_status()
        cap_status = "ok" if ms == "ok" else (
            "degraded" if ms == "degraded" else "unknown")
        components["capabilities"] = ComponentHealth(
            name="capabilities", status=cap_status, lastCheckAt=now)
    else:
        components["capabilities"] = ComponentHealth(
            name="capabilities", status="error", detail="not initialized")

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
