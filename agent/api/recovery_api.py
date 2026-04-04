"""Recovery API — B-023 (Sprint 52).

Admin endpoints for detecting and recovering corrupted mission state.
"""
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends

from auth.middleware import require_operator

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger("mcc.api.recovery")

OC_ROOT = Path(__file__).resolve().parent.parent.parent
MISSIONS_DIR = OC_ROOT / "logs" / "missions"

# Ensure tools path
sys.path.insert(0, str(OC_ROOT / "tools"))


def _meta() -> dict:
    return {
        "freshnessMs": 0,
        "dataQuality": "fresh",
        "sourcesUsed": [{"name": "recovery_scanner", "ageMs": 0, "status": "fresh"}],
        "sourcesMissing": [],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/recovery/scan")
async def scan_corruption():
    """Scan mission files for corruption issues."""
    from recovery import scan_missions
    issues = scan_missions(MISSIONS_DIR)
    return {
        "meta": _meta(),
        "issues": [i.to_dict() for i in issues],
        "count": len(issues),
        "repairable": sum(1 for i in issues if i.repairable),
    }


@router.post("/recovery/repair")
async def repair_corrupted(_operator=Depends(require_operator)):
    """Attempt to repair corrupted mission files."""
    from recovery import repair_truncated, scan_missions
    issues = scan_missions(MISSIONS_DIR)
    repaired = 0
    failed = 0
    results = []
    for issue in issues:
        if issue.repairable and issue.issue_type == "invalid_json":
            success = repair_truncated(issue.path)
            if success:
                repaired += 1
                results.append({"file": issue.path.name, "action": "repaired"})
            else:
                failed += 1
                results.append({"file": issue.path.name, "action": "repair_failed"})

    return {
        "meta": _meta(),
        "total_issues": len(issues),
        "repaired": repaired,
        "failed": failed,
        "results": results,
    }


@router.post("/recovery/quarantine")
async def quarantine_corrupted(_operator=Depends(require_operator)):
    """Move corrupted mission files to quarantine."""
    from recovery import quarantine_file, scan_missions
    issues = scan_missions(MISSIONS_DIR)
    quarantined = 0
    results = []
    for issue in issues:
        if issue.path.exists():
            dest = quarantine_file(issue.path)
            quarantined += 1
            results.append({
                "file": issue.path.name,
                "action": "quarantined",
                "destination": dest.name,
            })

    return {
        "meta": _meta(),
        "total_issues": len(issues),
        "quarantined": quarantined,
        "results": results,
    }
