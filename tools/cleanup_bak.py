"""Stale .bak file scanner and cleaner.

Sprint 56 Task 56.2 (B-028): Detect and remove accumulated .bak files.
Scans repo root and backup directories for stale backup artifacts.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

logger = logging.getLogger("mcc.tools.cleanup_bak")

SCRIPT_DIR = Path(__file__).resolve().parent
OC_ROOT = SCRIPT_DIR.parent

# Default max age for .bak files (30 days)
DEFAULT_MAX_AGE_DAYS = 30

# Directories to scan (relative to OC_ROOT)
SCAN_DIRS = [
    ".",
    "backups",
    "logs",
    "config",
    "agent",
    "tools",
]

# File patterns to match
BAK_PATTERNS = {".bak", ".bak.json", ".backup", ".old"}


def is_bak_file(path: Path) -> bool:
    """Check if a file is a backup/stale file."""
    name = path.name.lower()
    for pattern in BAK_PATTERNS:
        if name.endswith(pattern):
            return True
    if ".bak" in name:
        return True
    return False


def scan_bak_files(
    root: Path | None = None,
    scan_dirs: list[str] | None = None,
) -> list[dict]:
    """Scan for .bak files in configured directories.

    Returns list of file info dicts sorted by age (oldest first).
    """
    if root is None:
        root = OC_ROOT
    if scan_dirs is None:
        scan_dirs = SCAN_DIRS

    results = []
    now = time.time()

    for scan_dir in scan_dirs:
        target = root / scan_dir
        if not target.exists():
            continue

        for dirpath, _dirnames, filenames in os.walk(target):
            # Skip .git, node_modules, __pycache__
            dp = Path(dirpath)
            parts = dp.parts
            if any(p in (".git", "node_modules", "__pycache__", ".venv") for p in parts):
                continue

            for fname in filenames:
                fpath = dp / fname
                if is_bak_file(fpath):
                    try:
                        stat = fpath.stat()
                        results.append({
                            "path": str(fpath),
                            "name": fname,
                            "relative": str(fpath.relative_to(root)),
                            "size": stat.st_size,
                            "mtime": stat.st_mtime,
                            "age_days": (now - stat.st_mtime) / 86400,
                        })
                    except OSError:
                        continue

    results.sort(key=lambda x: x["mtime"])
    return results


def cleanup_bak_files(
    root: Path | None = None,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    dry_run: bool = False,
    scan_dirs: list[str] | None = None,
) -> dict:
    """Remove stale .bak files exceeding max_age_days.

    Returns summary dict with counts and details.
    """
    all_bak = scan_bak_files(root, scan_dirs)
    now = time.time()
    cutoff = now - (max_age_days * 86400)

    stale = [f for f in all_bak if f["mtime"] < cutoff]

    removed = []
    errors = []
    bytes_freed = 0

    for entry in stale:
        path = Path(entry["path"])
        if dry_run:
            removed.append(entry["relative"])
            bytes_freed += entry["size"]
        else:
            try:
                os.remove(path)
                removed.append(entry["relative"])
                bytes_freed += entry["size"]
                logger.info("Removed stale .bak: %s (age=%.1f days)", entry["relative"], entry["age_days"])
            except OSError as e:
                errors.append({"file": entry["relative"], "error": str(e)})
                logger.warning("Failed to remove .bak: %s — %s", entry["relative"], e)

    return {
        "total_bak_files": len(all_bak),
        "stale_count": len(stale),
        "removed": len(removed),
        "removed_files": removed,
        "bytes_freed": bytes_freed,
        "errors": errors,
        "dry_run": dry_run,
        "policy": {
            "max_age_days": max_age_days,
        },
    }


def status(root: Path | None = None) -> dict:
    """Return current .bak file status without modifying anything."""
    all_bak = scan_bak_files(root)
    total_size = sum(f["size"] for f in all_bak)

    return {
        "total_bak_files": len(all_bak),
        "total_size_bytes": total_size,
        "files": [
            {
                "relative": f["relative"],
                "size": f["size"],
                "age_days": round(f["age_days"], 1),
            }
            for f in all_bak
        ],
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Vezir .bak file cleanup")
    parser.add_argument("--max-age", type=int, default=DEFAULT_MAX_AGE_DAYS,
                        help=f"Max age in days (default: {DEFAULT_MAX_AGE_DAYS})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview deletions without removing files")
    parser.add_argument("--status", action="store_true",
                        help="Show .bak file status only")
    args = parser.parse_args()

    if args.status:
        import json
        result = status()
        print(json.dumps(result, indent=2))
    else:
        result = cleanup_bak_files(max_age_days=args.max_age, dry_run=args.dry_run)
        mode = "DRY RUN" if result["dry_run"] else "CLEANUP"
        print(f"Vezir .bak File {mode}")
        print(f"  Total .bak files: {result['total_bak_files']}")
        print(f"  Stale (>{args.max_age}d):  {result['stale_count']}")
        print(f"  Removed:          {result['removed']}")
        print(f"  Bytes freed:      {result['bytes_freed']}")
        if result["errors"]:
            print(f"  Errors:           {len(result['errors'])}")
        print("  Status: OK")


if __name__ == "__main__":
    main()
