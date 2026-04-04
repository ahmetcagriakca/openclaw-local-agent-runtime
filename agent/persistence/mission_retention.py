"""Mission retention — configurable cleanup for mission log files.

Sprint 56 Task 56.1 (B-027): Systematic retention for task/mission directories.
Age-based + count-based retention with bounded cleanup.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

logger = logging.getLogger("mcc.persistence.retention")

DEFAULT_MAX_AGE_DAYS = 90
DEFAULT_MAX_FILES = 5000
DEFAULT_MISSION_DIR = "logs/missions"


class MissionRetentionPolicy:
    """Configurable retention policy for mission log files.

    Supports:
    - Age-based cleanup (remove files older than max_age_days)
    - Count-based trim (keep at most max_files, oldest first)
    - Dry-run mode for previewing deletions
    - Summary/detail file pairing (mission + mission-summary)
    """

    def __init__(
        self,
        mission_dir: str | Path | None = None,
        max_age_days: int = DEFAULT_MAX_AGE_DAYS,
        max_files: int = DEFAULT_MAX_FILES,
    ):
        if mission_dir is None:
            from pathlib import Path as P
            mission_dir = P(__file__).resolve().parent.parent.parent / DEFAULT_MISSION_DIR
        self.mission_dir = Path(mission_dir)
        self.max_age_days = max_age_days
        self.max_files = max_files

    def scan(self) -> list[dict]:
        """Scan mission directory and return file info sorted by mtime (oldest first)."""
        if not self.mission_dir.exists():
            return []

        files = []
        for f in self.mission_dir.iterdir():
            if f.is_file() and f.suffix == ".json":
                stat = f.stat()
                files.append({
                    "path": str(f),
                    "name": f.name,
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "age_days": (time.time() - stat.st_mtime) / 86400,
                })
        files.sort(key=lambda x: x["mtime"])
        return files

    def identify_expired(self, files: list[dict] | None = None) -> list[dict]:
        """Identify files that exceed the age limit."""
        if files is None:
            files = self.scan()
        now = time.time()
        cutoff = now - (self.max_age_days * 86400)
        return [f for f in files if f["mtime"] < cutoff]

    def identify_overflow(self, files: list[dict] | None = None) -> list[dict]:
        """Identify oldest files that exceed the count limit."""
        if files is None:
            files = self.scan()
        if len(files) <= self.max_files:
            return []
        overflow_count = len(files) - self.max_files
        return files[:overflow_count]

    def identify_candidates(self, files: list[dict] | None = None) -> list[dict]:
        """Union of expired + overflow candidates (deduplicated)."""
        if files is None:
            files = self.scan()
        expired = self.identify_expired(files)
        overflow = self.identify_overflow(files)
        seen = set()
        result = []
        for f in expired + overflow:
            if f["name"] not in seen:
                seen.add(f["name"])
                result.append(f)
        return result

    def cleanup(self, dry_run: bool = False, max_batch: int = 500) -> dict:
        """Execute retention cleanup.

        Returns summary dict with counts and details.
        """
        files = self.scan()
        candidates = self.identify_candidates(files)

        # Bounded batch
        if len(candidates) > max_batch:
            candidates = candidates[:max_batch]

        removed = []
        errors = []
        bytes_freed = 0

        for entry in candidates:
            path = Path(entry["path"])
            if dry_run:
                removed.append(entry["name"])
                bytes_freed += entry["size"]
            else:
                try:
                    os.remove(path)
                    removed.append(entry["name"])
                    bytes_freed += entry["size"]
                    logger.info("Retention removed: %s (age=%.1f days)", entry["name"], entry["age_days"])
                except OSError as e:
                    errors.append({"file": entry["name"], "error": str(e)})
                    logger.warning("Retention remove failed: %s — %s", entry["name"], e)

        result = {
            "total_files": len(files),
            "candidates": len(candidates),
            "removed": len(removed),
            "removed_files": removed,
            "bytes_freed": bytes_freed,
            "errors": errors,
            "dry_run": dry_run,
            "policy": {
                "max_age_days": self.max_age_days,
                "max_files": self.max_files,
            },
        }

        if not dry_run:
            logger.info(
                "Mission retention: removed=%d, freed=%d bytes, errors=%d",
                result["removed"], bytes_freed, len(errors),
            )

        return result

    def status(self) -> dict:
        """Return current retention status without modifying anything."""
        files = self.scan()
        expired = self.identify_expired(files)
        overflow = self.identify_overflow(files)
        candidates = self.identify_candidates(files)

        total_size = sum(f["size"] for f in files)
        oldest = files[0] if files else None
        newest = files[-1] if files else None

        return {
            "total_files": len(files),
            "total_size_bytes": total_size,
            "expired_count": len(expired),
            "overflow_count": len(overflow),
            "cleanup_candidates": len(candidates),
            "oldest_file": oldest["name"] if oldest else None,
            "oldest_age_days": round(oldest["age_days"], 1) if oldest else None,
            "newest_file": newest["name"] if newest else None,
            "newest_age_days": round(newest["age_days"], 1) if newest else None,
            "policy": {
                "max_age_days": self.max_age_days,
                "max_files": self.max_files,
            },
        }
