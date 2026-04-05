"""Mission Retention API — B-027 (Sprint 56).

Endpoints for mission directory retention status and cleanup.
Requires operator auth for cleanup mutations.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from auth.middleware import require_operator

router = APIRouter(prefix="/admin/retention", tags=["admin"])
logger = logging.getLogger("mcc.api.retention")


def _meta() -> dict:
    return {
        "freshnessMs": 0,
        "dataQuality": "fresh",
        "sourcesUsed": [{"name": "retention_store", "ageMs": 0, "status": "fresh"}],
        "sourcesMissing": [],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/missions/status")
def retention_status():
    """Get current mission retention status and policy."""
    from persistence.mission_retention import MissionRetentionPolicy
    policy = MissionRetentionPolicy()
    return {"data": policy.status(), "_meta": _meta()}


@router.get("/missions/candidates")
def retention_candidates(
    max_age_days: int = Query(90, ge=1, le=365),
    max_files: int = Query(5000, ge=100, le=50000),
):
    """List files that would be cleaned up by retention policy."""
    from persistence.mission_retention import MissionRetentionPolicy
    policy = MissionRetentionPolicy(max_age_days=max_age_days, max_files=max_files)
    candidates = policy.identify_candidates()
    return {
        "data": {
            "count": len(candidates),
            "files": [{"name": c["name"], "age_days": round(c["age_days"], 1), "size": c["size"]} for c in candidates[:100]],
            "truncated": len(candidates) > 100,
        },
        "_meta": _meta(),
    }


@router.post("/missions/cleanup")
def retention_cleanup(
    max_age_days: int = Query(90, ge=1, le=365),
    max_files: int = Query(5000, ge=100, le=50000),
    dry_run: bool = Query(True),
    _operator=Depends(require_operator),
):
    """Execute retention cleanup. Dry-run by default."""
    from persistence.mission_retention import MissionRetentionPolicy
    try:
        policy = MissionRetentionPolicy(max_age_days=max_age_days, max_files=max_files)
        result = policy.cleanup(dry_run=dry_run)
        logger.info("Retention cleanup: dry_run=%s, removed=%d", dry_run, result["removed"])
        return {"data": result, "_meta": _meta()}
    except HTTPException:
        raise
    except Exception:
        logger.error("Retention cleanup failed")
        raise HTTPException(status_code=500, detail="Retention cleanup failed")  # noqa: B904


@router.get("/bak/status")
def bak_status():
    """Get current .bak file status."""
    import sys
    from pathlib import Path as P
    tools_dir = str(P(__file__).resolve().parent.parent.parent / "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    from cleanup_bak import status as _bak_status
    return {"data": _bak_status(), "_meta": _meta()}


@router.post("/bak/cleanup")
def bak_cleanup(
    max_age_days: int = Query(30, ge=1, le=365),
    dry_run: bool = Query(True),
    _operator=Depends(require_operator),
):
    """Clean up stale .bak files. Dry-run by default."""
    import sys
    from pathlib import Path as P
    tools_dir = str(P(__file__).resolve().parent.parent.parent / "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    from cleanup_bak import cleanup_bak_files
    result = cleanup_bak_files(max_age_days=max_age_days, dry_run=dry_run)
    logger.info("Bak cleanup: dry_run=%s, removed=%d", dry_run, result["removed"])
    return {"data": result, "_meta": _meta()}
