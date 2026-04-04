"""Backup & Restore API — B-022 (Sprint 51).

Admin endpoints for creating backups and restoring from them.
Requires operator auth for all mutations.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from auth.middleware import require_operator

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger("mcc.api.backup")

# Paths
OC_ROOT = Path(__file__).resolve().parent.parent.parent
BACKUPS_DIR = OC_ROOT / "backups"


def _meta() -> dict:
    return {
        "freshnessMs": 0,
        "dataQuality": "fresh",
        "sourcesUsed": [{"name": "backup_store", "ageMs": 0, "status": "fresh"}],
        "sourcesMissing": [],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/backups")
async def list_backups():
    """List available backups."""
    backups = []
    if BACKUPS_DIR.exists():
        for item in sorted(BACKUPS_DIR.iterdir(), reverse=True):
            if item.is_dir() and item.name.startswith("backup-"):
                manifest_path = item / "manifest.json"
                if manifest_path.exists():
                    manifest = json.loads(
                        manifest_path.read_text(encoding="utf-8"))
                    backups.append({
                        "name": item.name,
                        "created_at": manifest.get("created_at", ""),
                        "file_count": manifest.get("file_count", 0),
                        "path": str(item),
                    })
    return {
        "meta": _meta(),
        "backups": backups,
        "count": len(backups),
    }


@router.post("/backup")
async def create_backup(
    include_missions: bool = True,
    include_configs: bool = True,
    _operator=Depends(require_operator),
):
    """Create a new backup snapshot."""
    import sys
    sys.path.insert(0, str(OC_ROOT / "tools"))
    from backup import create_backup as do_backup

    try:
        backup_path = do_backup(
            output_dir=BACKUPS_DIR,
            include_missions=include_missions,
            include_configs=include_configs,
        )
        manifest = json.loads(
            (backup_path / "manifest.json").read_text(encoding="utf-8"))
        logger.info("Backup created: %s (%d files)",
                     backup_path.name, manifest["file_count"])
        return {
            "meta": _meta(),
            "backup": {
                "name": backup_path.name,
                "created_at": manifest.get("created_at", ""),
                "file_count": manifest.get("file_count", 0),
                "path": str(backup_path),
            },
            "status": "created",
        }
    except Exception as e:
        logger.error("Backup failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Backup failed: {e}")


@router.post("/restore")
async def restore_from_backup(
    backup_name: str,
    dry_run: bool = True,
    _operator=Depends(require_operator),
):
    """Restore from a backup. Defaults to dry_run=true for safety."""
    import sys
    sys.path.insert(0, str(OC_ROOT / "tools"))
    from restore import restore_backup, validate_backup

    backup_dir = BACKUPS_DIR / backup_name
    if not backup_dir.exists():
        raise HTTPException(status_code=404, detail=f"Backup not found: {backup_name}")

    # Validate integrity
    valid, errors = validate_backup(backup_dir)
    if not valid:
        raise HTTPException(
            status_code=422,
            detail=f"Backup integrity check failed: {'; '.join(errors)}"
        )

    restored, warnings = restore_backup(backup_dir, dry_run=dry_run)
    action = "dry_run" if dry_run else "restored"
    logger.info("Restore %s: %s (%d files)", action, backup_name, restored)

    return {
        "meta": _meta(),
        "action": action,
        "backup_name": backup_name,
        "files_affected": restored,
        "warnings": warnings,
    }
