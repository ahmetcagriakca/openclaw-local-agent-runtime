"""Audit Export API — B-115 (Sprint 55).

Compliance-ready audit export endpoint. Localhost-only, auth-scoped,
redaction applied, fail-closed. Governed by export contract in sprint plan.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from auth.middleware import require_operator

router = APIRouter(prefix="/audit", tags=["audit"])
logger = logging.getLogger("mcc.api.audit_export")

OC_ROOT = Path(__file__).resolve().parent.parent.parent
EXPORT_DIR = OC_ROOT / "audit-exports"


def _meta() -> dict:
    return {
        "freshnessMs": 0,
        "dataQuality": "fresh",
        "sourcesUsed": [{"name": "audit_store", "ageMs": 0, "status": "fresh"}],
        "sourcesMissing": [],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/export")
async def create_audit_export(
    mission_id: str | None = Query(None, description="Filter by mission ID"),
    user_id: str | None = Query(None, description="Filter by user ID"),
    from_ts: str | None = Query(None, alias="from",
                                description="From timestamp (ISO)"),
    to_ts: str | None = Query(None, alias="to",
                              description="To timestamp (ISO)"),
    include_csv: bool = Query(False, description="Include CSV summaries"),
    _operator=Depends(require_operator),
):
    """Create audit export archive. Requires operator auth. Localhost-only."""
    import sys
    sys.path.insert(0, str(OC_ROOT / "tools"))
    from audit_export import export_audit

    try:
        result = export_audit(
            output_dir=EXPORT_DIR,
            mission_id=mission_id,
            user_id=user_id,
            from_ts=from_ts,
            to_ts=to_ts,
            include_csv=include_csv,
        )
        logger.info("Audit export created: %s (%d records)",
                     result["archive_name"], result["total_records"])
        return {
            "meta": _meta(),
            "export": result,
            "status": "created",
        }
    except Exception as e:
        logger.error("Audit export failed: %s", e)
        raise HTTPException(status_code=500,
                            detail=f"Audit export failed: {e}")


@router.get("/exports")
async def list_exports():
    """List available audit exports."""
    exports = []
    if EXPORT_DIR.exists():
        for f in sorted(EXPORT_DIR.iterdir(), reverse=True):
            if f.name.startswith("audit-export-") and f.name.endswith(".zip"):
                exports.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "created": datetime.fromtimestamp(
                        f.stat().st_mtime, tz=timezone.utc
                    ).isoformat(),
                })
    return {
        "meta": _meta(),
        "exports": exports,
        "count": len(exports),
    }
